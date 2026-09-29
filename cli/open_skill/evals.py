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
# catches and the near misses it leaves alone. Each file in evals/triggers/ labels ~20 queries for one skill.


def load_trigger_sets(folder: Path | None = None) -> dict[str, list[dict]]:
    """skill name -> [{"q": query, "trigger": bool}, ...]"""
    folder = Path(folder) if folder else paths.data_root() / "evals" / "triggers"
    out = {}
    for p in sorted(folder.glob("*.yaml")):
        doc = yaml.safe_load(p.read_text())
        queries = doc.get("queries", [])
        if not all(isinstance(q.get("q"), str) and isinstance(q.get("trigger"), bool) for q in queries):
            raise ValueError(f"{p}: every query needs a string 'q' and a boolean 'trigger'")
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
