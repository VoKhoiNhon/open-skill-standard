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
