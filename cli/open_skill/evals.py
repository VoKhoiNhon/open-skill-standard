"""Evaluation of routing (deterministic) and of skill triggering (lexical proxy or a real agent)."""

import tempfile
from pathlib import Path

import yaml

from . import paths, route
from .scan import Installed


def all_installed(reg) -> list[Installed]:
    """Pretend every registry skill is installed, so evals measure routing rather than one machine's setup."""
    return [Installed(sid, sid.split("/", 1)[1], "/eval", s.get("description", ""), False) for sid, s in reg.skills.items()]


def load_routing_cases(path: Path | None = None) -> list[dict]:
    path = Path(path) if path else paths.data_root() / "evals" / "routing.yaml"
    return yaml.safe_load(path.read_text())["cases"]


def run_case(case: dict, reg, installed) -> list[str]:
    """Run one routing case in a scratch project; return the list of failed expectations (empty = pass)."""
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp)
        for f in case.get("files", []):
            (proj / f).parent.mkdir(parents=True, exist_ok=True)
            (proj / f).write_text("x")
        r = route.route(case["task"], proj, reg, installed, role=case.get("role"), size=case.get("size"),
                        model=case.get("model"), record=False)
    ids = [s["id"] for s in r["chain"]]
    shown = " → ".join(f"{s['phase']}:{s['id']}" for s in r["chain"]) or str(r["advice"])
    fails = [f"{sid} missing from {shown}" for sid in case.get("include", []) if sid not in ids]
    fails += [f"{sid} unexpectedly in {shown}" for sid in case.get("exclude", []) if sid in ids]
    if "first" in case and (not ids or ids[0] != case["first"]):
        fails.append(f"first step should be {case['first']}: {shown}")
    if "phases" in case and [s["phase"] for s in r["chain"]] != case["phases"]:
        fails.append(f"phases should be {case['phases']}: {shown}")
    if "advice" in case and r["advice"] != case["advice"]:
        fails.append(f"advice should be {case['advice']}: {shown}")
    if "max_steps" in case and len(ids) > case["max_steps"]:
        fails.append(f"at most {case['max_steps']} steps: {shown}")
    if "last_phase" in case and (not r["chain"] or r["chain"][-1]["phase"] != case["last_phase"]):
        fails.append(f"last phase should be {case['last_phase']}: {shown}")
    return fails


def routing_report(cases: list[dict], reg, installed) -> dict:
    """Pass/fail per case and per role, for people tuning role packs and adapters."""
    results, by_role = [], {}
    for case in cases:
        fails = run_case(case, reg, installed)
        results.append({"id": case["id"], "role": case.get("role"), "passed": not fails, "failures": fails})
        row = by_role.setdefault(case.get("role") or "-", {"cases": 0, "passed": 0})
        row["cases"] += 1
        row["passed"] += not fails
    passed = sum(r["passed"] for r in results)
    return {"cases": len(results), "passed": passed, "pass_rate": round(passed / max(len(results), 1), 3),
            "by_role": dict(sorted(by_role.items())), "results": results}


# ---------------------------------------------------------------- trigger evals
# Agents pick a skill from its name and description alone, so a description is only as good as the queries it
# catches and the near misses it leaves alone. Each file in evals/triggers/ labels ~30 queries for one skill;
# queries marked `holdout: true` are kept out of tuning and only show whether a description generalizes.


def load_trigger_sets(folder: Path | None = None) -> dict[str, list[dict]]:
    """skill name -> [{"q": query, "trigger": bool, "holdout": bool (optional)}, ...]"""
    folder = Path(folder) if folder else paths.data_root() / "evals" / "triggers"
    out = {}
    for p in sorted(folder.glob("*.yaml")):
        doc = yaml.safe_load(p.read_text())
        queries = doc.get("queries", [])
        if not all(isinstance(q.get("q"), str) and isinstance(q.get("trigger"), bool) for q in queries):
            raise ValueError(f"{p}: every query needs a string 'q' and a boolean 'trigger'")
        if not all(isinstance(q.get("holdout", False), bool) for q in queries):
            raise ValueError(f"{p}: 'holdout' must be true or false")
        out[doc["skill"]] = queries
    return out


def skill_descriptions(reg, skills_dir: Path | None = None) -> dict[str, str]:
    """What an agent sees for each skill: SKILL.md descriptions for local skills, registry text for the rest."""
    from . import frontmatter

    out = {sid.split("/", 1)[1]: s.get("description", "") for sid, s in reg.skills.items()}
    for p in sorted((Path(skills_dir) if skills_dir else paths.data_root() / "skills").glob("*/SKILL.md")):
        meta, _ = frontmatter.parse(p.read_text())
        if meta.get("name"):
            out[meta["name"]] = str(meta.get("description", ""))
    return out


def lexical_triggers(query: str, descriptions: dict[str, str], top_k: int = 3, ratio: float = 0.5) -> list[str]:
    """Deterministic stand-in for an agent's choice: skills in the top k by BM25 and within `ratio` of the best."""
    import sqlite3

    from . import index

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE VIRTUAL TABLE d USING fts5(name UNINDEXED, text, tokenize='unicode61 remove_diacritics 2')")
    conn.executemany("INSERT INTO d VALUES (?, ?)", [(n, f"{n.replace('-', ' ')} {t}") for n, t in descriptions.items()])
    tokens = [t for t in index.TOKEN.findall(query.lower()) if t not in index.STOP and t != "near"]
    if not tokens:
        return []
    rows = conn.execute("SELECT name, -bm25(d) FROM d WHERE d MATCH ? ORDER BY bm25(d) LIMIT ?",
                        (" OR ".join(f'"{t}"' for t in dict.fromkeys(tokens)), top_k)).fetchall()
    if not rows:
        return []
    best = rows[0][1]
    return [name for name, score in rows if score >= best * ratio]


def trigger_metrics(labels: list[dict], fired: list[bool]) -> dict:
    tp = sum(1 for q, f in zip(labels, fired) if q["trigger"] and f)
    fp = sum(1 for q, f in zip(labels, fired) if not q["trigger"] and f)
    fn = sum(1 for q, f in zip(labels, fired) if q["trigger"] and not f)
    tn = len(labels) - tp - fp - fn
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(tp / (tp + fp), 3) if tp + fp else 1.0,
            "recall": round(tp / (tp + fn), 3) if tp + fn else 1.0,
            "missed": [q["q"] for q, f in zip(labels, fired) if q["trigger"] and not f],
            "false_alarms": [q["q"] for q, f in zip(labels, fired) if not q["trigger"] and f]}


def trigger_report_lexical(sets: dict[str, list[dict]], descriptions: dict[str, str]) -> dict[str, dict]:
    return {skill: trigger_metrics(qs, [skill in lexical_triggers(q["q"], descriptions) for q in qs])
            for skill, qs in sets.items()}


def invoked_skills(stream_json: str) -> set[str]:
    """Skill names an agent invoked, from Claude Code `--output-format stream-json` output."""
    import json

    found = set()
    for line in stream_json.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        for block in (event.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Skill":
                name = str((block.get("input") or {}).get("skill", ""))
                if name:
                    found.add(name.split(":")[-1])  # "plugin:skill" -> "skill"
    return found


def claude_runner(timeout: int = 180):
    """Run one query through Claude Code headless and return the skills it invoked."""
    import subprocess

    def run(query: str) -> set[str]:
        out = subprocess.run(["claude", "-p", query, "--output-format", "stream-json", "--verbose", "--max-turns", "2"],
                             capture_output=True, text=True, timeout=timeout)
        return invoked_skills(out.stdout)

    return run


def split_queries(queries: list[dict], train_share: float = 0.6) -> tuple[list[dict], list[dict]]:
    """Train/validation split: the `holdout` flags when a set has them, else a stable hash split stratified by label,
    so tuning cannot peek at validation."""
    import hashlib

    if any("holdout" in q for q in queries):
        return [q for q in queries if not q.get("holdout")], [q for q in queries if q.get("holdout")]
    train, val = [], []
    for label in (True, False):
        group = sorted((q for q in queries if q["trigger"] is label), key=lambda q: hashlib.sha1(q["q"].encode()).hexdigest())
        cut = round(len(group) * train_share)
        train += group[:cut]
        val += group[cut:]
    return train, val


def trigger_report_agent(sets: dict[str, list[dict]], runner, runs: int = 3, threshold: float = 0.5) -> dict[str, dict]:
    """Run each query `runs` times; a skill counts as triggered when its invocation rate reaches `threshold`."""
    report = {}
    for skill, queries in sets.items():
        rates = {}
        for q in queries:
            hits = sum(skill in runner(q["q"]) for _ in range(runs))
            rates[q["q"]] = hits / runs
        train, val = split_queries(queries)
        report[skill] = {
            "train": trigger_metrics(train, [rates[q["q"]] >= threshold for q in train]),
            "validation": trigger_metrics(val, [rates[q["q"]] >= threshold for q in val]),
            "rates": rates,
        }
    return report
