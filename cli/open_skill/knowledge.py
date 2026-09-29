"""The user layer (L2): profile, knowledge nodes, usage events, personal weights. Local files only."""

import datetime as dt
import hashlib
import json
import re
import shutil
import time
from pathlib import Path

import yaml

from . import frontmatter, paths

HALF_LIFE_DAYS = 90
WEIGHT_RANGE = (-0.9, 2.0)
SENSITIVE = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("phone", re.compile(r"(?<![\w-])(\+\d{1,3}[ .-]?)?(\(?\d{2,4}\)?[ .-]){2,}\d{3,4}(?![\w-])")),
    ("api-token", re.compile(r"\b(sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|xox[abp]-[\w-]{10,})")),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("password", re.compile(r"(?i)\b(password|passwd|pwd|secret)\s*[=:]")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
MEMORY_TYPES = {"feedback": "preference", "user": "preference", "project": "project-fact", "reference": "glossary"}


def home() -> Path:
    return paths.user_home()


def _kdir() -> Path:
    d = home() / "knowledge"
    d.mkdir(parents=True, exist_ok=True)
    return d


def looks_sensitive(text: str) -> str | None:
    """Name of the first sensitive pattern found, or None."""
    return next((name for name, rx in SENSITIVE if rx.search(text)), None)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _node_id(text: str) -> str:
    digest = hashlib.sha1(_norm(text).encode()).hexdigest()[:8]
    slug = "-".join(re.findall(r"[a-z0-9]+", _norm(text))[:5])[:40] or "note"
    return f"k-{slug}-{digest}"


def _write(meta: dict, text: str) -> None:
    body = "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n" + text.strip() + "\n"
    (_kdir() / f"{meta['id']}.md").write_text(body)


def learn(text: str, applies_to: list[str], type_: str = "lesson", force: bool = False, source: str = "user") -> str:
    """Store one fact per file; the same text updates the existing node instead of duplicating it."""
    reason = looks_sensitive(text)
    if reason and not force:
        raise ValueError(f"refusing to store text that looks like {reason}; pass force=True to override")
    nid = _node_id(text)
    path = _kdir() / f"{nid}.md"
    if path.exists():
        meta, _ = frontmatter.parse(path.read_text())
        meta["applies_to"] = list(dict.fromkeys([*meta.get("applies_to", []), *applies_to]))
        meta["updated"] = dt.date.today().isoformat()
    else:
        meta = {"id": nid, "kind": "knowledge", "type": type_, "applies_to": list(applies_to), "source": source,
                "created": dt.date.today().isoformat(), "summary": text.strip().splitlines()[0][:120]}
    _write(meta, text)
    return nid


def forget(node_id: str) -> bool:
    path = _kdir() / f"{node_id}.md"
    if not path.exists():
        return False
    path.unlink()
    return True


def load_knowledge() -> list[dict]:
    out = []
    for p in sorted(_kdir().glob("*.md")):
        meta, body = frontmatter.parse(p.read_text())
        if meta.get("id"):
            out.append({**meta, "text": body.strip()})
    return out


def init(profile: dict, seeds: dict[str, list[str]]) -> Path:
    """Write profile.yaml and copy the seeds of the chosen roles into knowledge/."""
    home().mkdir(parents=True, exist_ok=True)
    (home() / "profile.yaml").write_text(yaml.safe_dump(profile, sort_keys=False, allow_unicode=True))
    for role in profile.get("roles", {}):
        for s in seeds.get(role, []):
            learn(s, [f"role:{role}"], type_="pitfall", source="seed")
    return home()


def load_profile() -> dict:
    p = home() / "profile.yaml"
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def record(event: dict) -> None:
    event = {"ts": time.time(), **event}
    home().mkdir(parents=True, exist_ok=True)
    with (home() / "events.jsonl").open("a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _events() -> list[dict]:
    p = home() / "events.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def personal_weights(now: float | None = None) -> dict[str, float]:
    """+1 for skills proposed and run (or run unproposed), -1 for proposed but skipped; halved every 90 days."""
    now = now or time.time()
    events = _events()
    proposed = {e["route_id"]: e.get("chain", []) for e in events if e.get("type") == "proposed"}
    weights: dict[str, float] = {}
    for e in events:
        if e.get("type") != "feedback" or e.get("route_id") not in proposed:
            continue
        decay = 0.5 ** ((now - e.get("ts", now)) / 86400 / HALF_LIFE_DAYS)
        chain = proposed[e["route_id"]]
        by_invoke = {step["invoke"]: step["id"] for step in chain}
        ran = {by_invoke.get(inv, f"invoke:{inv}") for inv in e.get("ran", [])}
        good = 1.0 if e.get("outcome", "ok") == "ok" else 0.5
        for sid in ran:
            weights[sid] = weights.get(sid, 0.0) + good * decay
        for step in chain:
            if step["id"] not in ran:
                weights[step["id"]] = weights.get(step["id"], 0.0) - decay
    lo, hi = WEIGHT_RANGE
    return {k: max(lo, min(hi, v)) for k, v in weights.items()}


def export(dest: Path) -> Path:
    """Zip of profile.yaml + knowledge/ (events stay on this machine)."""
    stage = Path(dest).with_suffix("")
    tmp = stage.parent / (stage.name + ".staging")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    if (home() / "profile.yaml").exists():
        shutil.copy(home() / "profile.yaml", tmp / "profile.yaml")
    shutil.copytree(_kdir(), tmp / "knowledge")
    out = shutil.make_archive(str(stage), "zip", tmp)
    shutil.rmtree(tmp)
    return Path(out)


def import_agent_memory(root: Path | None = None) -> int:
    """Read-only import of Claude Code memory files (<root>/*/memory/*.md) as knowledge nodes."""
    root = Path(root) if root else Path.home() / ".claude" / "projects"
    count = 0
    for p in sorted(root.glob("*/memory/*.md")):
        if p.name == "MEMORY.md":
            continue
        meta, body = frontmatter.parse(p.read_text(errors="replace"))
        text = body.strip()
        if not text or looks_sensitive(text):
            continue
        mtype = (meta.get("metadata") or {}).get("type") or meta.get("type")
        learn(text, ["role:*"], type_=MEMORY_TYPES.get(mtype, "preference"), source="agent-memory")
        count += 1
    return count
