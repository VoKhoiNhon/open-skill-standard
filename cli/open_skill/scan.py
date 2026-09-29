"""Find the skills actually installed on this machine and map them to registry ids."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

from . import frontmatter

# Generic locations searched for skills no adapter rule claims.
GENERIC = [
    "~/.claude/skills/*/SKILL.md",
    "~/.claude/plugins/cache/*/*/*/skills/*/SKILL.md",
    "{project}/.claude/skills/*/SKILL.md",
]


@dataclass
class Installed:
    id: str
    invoke: str
    path: str
    description: str
    inferred: bool


def _expand(pattern: str, project: Path | None) -> str | None:
    if "{project}" in pattern:
        if project is None:
            return None
        pattern = pattern.replace("{project}", str(Path(project).resolve()))
    return str(Path(pattern).expanduser()) if pattern.startswith("~") else pattern


def _regex(pattern: str) -> re.Pattern:
    out = re.escape(pattern).replace(r"\{name\}", "(?P<name>[^/]+)").replace(r"\*", "[^/]*")
    return re.compile(f"^{out}$")


def _glob(pattern: str) -> list[Path]:
    p = Path(pattern.replace("{name}", "*"))
    anchor = Path(p.anchor)
    return sorted(anchor.glob(str(p.relative_to(anchor))))


def _latest_versions(paths: list[Path]) -> list[Path]:
    """Keep only the newest plugin version when a cache holds several (…/<plugin>/<version>/skills/…)."""
    best: dict[tuple, Path] = {}
    for p in paths:
        parts = p.parts
        if "cache" in parts and "skills" in parts:
            i = parts.index("skills")
            key = parts[: i - 1] + parts[i:]
            if key not in best or parts[i - 1] > best[key].parts[i - 1]:
                best[key] = p
        else:
            best[(p,)] = p
    return sorted(best.values())


def _describe(path: Path) -> tuple[str, str]:
    meta, _ = frontmatter.parse(path.read_text(errors="replace"))
    return str(meta.get("name") or path.parent.name), str(meta.get("description") or "")


def scan(reg, project: Path | None = None) -> list[Installed]:
    found: dict[str, Installed] = {}
    claimed: set[Path] = set()
    for src, adapter in reg.adapters.items():
        known = {s["name"] for s in adapter.get("skills", [])}
        for rule in adapter.get("detect", []):
            pat = _expand(rule["glob"], project)
            if not pat:
                continue
            rx = _regex(pat)
            # A rule may claim skills the adapter does not list only if its path is specific
            # to this source (source name in the path, or a prefix like "speckit-{name}").
            specific = f"/{src}/" in rule["glob"] or not re.search(r"/\{name\}(/|$)", rule["glob"])
            for path in _latest_versions(_glob(pat)):
                m = rx.match(str(path))
                if not m:
                    continue
                name = m.group("name")
                if name not in known and not specific:
                    continue
                sid = f"{src}/{name}"
                claimed.add(path.resolve())
                if any(i.id == sid for i in found.values()):
                    continue  # an earlier rule already found this skill
                _, desc = _describe(path)
                inv = rule["invoke"].format(name=name)
                found[inv] = Installed(sid, inv, str(path), desc, inferred=name not in known)
    for src, adapter in reg.adapters.items():
        env = adapter.get("available_env")
        if env and os.environ.get(env):
            for s in adapter.get("skills", []):
                inv = s.get("invoke", s["name"])
                found.setdefault(inv, Installed(f"{src}/{s['name']}", inv, f"builtin:{env}", s.get("description", ""), False))
    for pattern in GENERIC:
        pat = _expand(pattern, project)
        if not pat:
            continue
        for path in _latest_versions(_glob(pat)):
            if path.resolve() in claimed:
                continue
            name, desc = _describe(path)
            parts = path.parts
            inv = f"{parts[parts.index('skills') - 2]}:{name}" if "cache" in parts else name
            if inv not in found:
                found[inv] = Installed(f"harvested/{name}", inv, str(path), desc, inferred=True)
    return sorted(found.values(), key=lambda i: i.invoke)
