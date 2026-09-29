import copy
from pathlib import Path

import pytest

from open_skill import registry, route
from open_skill.scan import Installed

FIX = Path(__file__).parent / "fixtures"
REG = registry.load(FIX / "repo")


def installed(reg, *ids):
    return [Installed(sid, sid.split("/")[1], "/x", reg.skills.get(sid, {}).get("description", ""), sid not in reg.skills)
            for sid in ids]


ALL = installed(REG, *REG.skills)


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "p"
    p.mkdir()
    return p


def run(task, project, reg=REG, inst=ALL, **kw):
    return route.route(task, project, reg, inst, role=kw.pop("role", "data-engineer"), record=False, **kw)


def outcomes(r, sid):
    return {d["phase"]: d for d in r["decisions"]["candidates"] if d["id"] == sid}


def test_default_output_has_no_decisions(project):
    assert "decisions" not in run("add an export endpoint", project)


def test_decisions_record_the_window_the_winner_and_the_losers(project):
    r = run("add an export endpoint", project, decisions=True)
    assert r["decisions"]["window"] == ["plan", "build", "verify", "review"]
    build = outcomes(r, "superpowers/test-driven-development")["build"]
    assert build["outcome"] == "chosen" and build["score"] == r["chain"][0]["score"]
    assert outcomes(r, "spec-kit/plan")["plan"] == {"phase": "plan", "id": "spec-kit/plan", "outcome": "requirement-unmet",
                                                    "needs": [".specify"]}
    assert outcomes(r, "claude-code-builtin/code-review")["plan"]["outcome"] == "wrong-phase"


def test_steps_dropped_by_the_model_limit_are_marked_trimmed(tmp_path):
    p = tmp_path / "p"
    for d in (".specify", ".codegraph"):
        (p / d).mkdir(parents=True)
    r = run("build a new platform", p, model="claude-haiku-4-5", decisions=True)
    kept = {s["id"] for s in r["chain"]}
    trimmed = [d for d in r["decisions"]["candidates"] if d["outcome"] == "trimmed"]
    assert trimmed and all(d["id"] not in kept and d["max_steps"] == 3 for d in trimmed)
    assert not [d for d in r["decisions"]["candidates"] if d["outcome"] == "chosen" and d["id"] not in kept]


def test_small_tasks_done_directly_mark_the_winner(project):
    r = run("fix typo in README", project, decisions=True)
    assert r["advice"] == "do directly"
    assert outcomes(r, "superpowers/test-driven-development")["build"]["outcome"] == "do-directly"
