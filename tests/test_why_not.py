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
    assert r["decisions"]["window_reason"] == "medium build task: starts at plan, then verify and review"
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


def reasons(r, sid, reg=REG, inst=ALL):
    return route.why_not(r, sid, reg, inst)


def test_why_not_installed(project):
    inst = [i for i in ALL if i.id != "superpowers/writing-plans"]
    w = reasons(run("add an export endpoint", project, inst=inst, decisions=True), "superpowers/writing-plans", inst=inst)
    assert w["chosen"] is None
    assert [x["code"] for x in w["reasons"]] == ["not-installed"]
    assert "npx skills add obra/superpowers -g" in w["reasons"][0]["text"]


def test_why_not_wrong_phase(project):
    w = reasons(run("review the diff", project, decisions=True), "superpowers/writing-plans")
    assert [x["code"] for x in w["reasons"]] == ["wrong-phase"]
    assert "plan" in w["reasons"][0]["text"] and "review" in w["reasons"][0]["text"]


def test_why_not_wrong_size(project):
    w = reasons(run("plan the export endpoint", project, size="small", decisions=True), "superpowers/writing-plans")
    assert [x["code"] for x in w["reasons"]] == ["wrong-size"]
    assert "small" in w["reasons"][0]["text"]


def test_why_not_requirement_unmet(project):
    w = reasons(run("add an export endpoint", project, decisions=True), "spec-kit/plan")
    assert [x["code"] for x in w["reasons"]] == ["requirement-unmet"]
    assert ".specify" in w["reasons"][0]["text"]


def test_why_not_conflict_with_a_chosen_skill(project):
    reg = copy.deepcopy(REG)
    reg.skills["claude-code-builtin/code-review"]["conflicts"] = ["superpowers/writing-plans"]
    inst = installed(reg, *reg.skills)
    r = run("add an export endpoint", project, reg=reg, inst=inst, decisions=True)
    assert "superpowers/writing-plans" in [s["id"] for s in r["chain"]]
    w = reasons(r, "claude-code-builtin/code-review", reg=reg, inst=inst)
    assert [x["code"] for x in w["reasons"]] == ["conflict"]
    assert "superpowers/writing-plans" in w["reasons"][0]["text"]


def test_why_not_lower_score_shows_both_scores(project):
    r = run("add an export endpoint", project, role="fullstack-developer", decisions=True)
    plan = next(s for s in r["chain"] if s["phase"] == "plan")
    loser = next(d for d in r["decisions"]["candidates"] if d["phase"] == "plan" and d["outcome"] == "lower-score")
    w = reasons(r, loser["id"])
    lost = next(x for x in w["reasons"] if x["code"] == "lower-score")
    assert plan["id"] in lost["text"] and str(loser["score"]) in lost["text"] and str(plan["score"]) in lost["text"]


def test_why_not_below_minimum(project):
    w = reasons(run("add an export endpoint", project, decisions=True), "superpowers/brainstorming")
    assert [x["code"] for x in w["reasons"]] == ["below-minimum"]
    assert str(route.MIN_SCORE) in w["reasons"][0]["text"]


def test_why_not_skill_without_manifest(project):
    inst = ALL + [Installed("harvested/notes", "notes", "/x", "Keep meeting notes tidy", True)]
    w = reasons(run("add an export endpoint", project, inst=inst, decisions=True), "harvested/notes", inst=inst)
    assert {x["code"] for x in w["reasons"]} == {"no-phase-keywords"}


def test_why_not_trimmed_and_do_directly(tmp_path, project):
    w = reasons(run("fix typo in README", project, decisions=True), "superpowers/test-driven-development")
    assert [x["code"] for x in w["reasons"]] == ["do-directly"]
    p = tmp_path / "q"
    for d in (".specify", ".codegraph"):
        (p / d).mkdir(parents=True)
    r = run("build a new platform", p, model="claude-haiku-4-5", decisions=True)
    gone = next(d["id"] for d in r["decisions"]["candidates"] if d["outcome"] == "trimmed")
    assert "trimmed" in [x["code"] for x in reasons(r, gone)["reasons"]]


def test_why_not_a_chosen_skill_says_so(project):
    r = run("add an export endpoint", project, decisions=True)
    w = reasons(r, r["chain"][0]["id"])
    assert w["chosen"] == r["chain"][0]["phase"] and w["reasons"] == []


def test_why_not_unknown_skill(project):
    with pytest.raises(KeyError):
        reasons(run("add an export endpoint", project, decisions=True), "nobody/nothing")


@pytest.mark.parametrize("task,kw", [
    ("add an export endpoint", {}),
    ("fix typo in README", {}),
    ("build a new platform", {"model": "claude-haiku-4-5"}),
    ("add an export endpoint", {"role": "fullstack-developer"}),
])
def test_decisions_never_change_the_route(project, task, kw):
    plain = run(task, project, **kw)
    traced = run(task, project, decisions=True, **kw)
    traced.pop("decisions")
    for r in (plain, traced):
        r.pop("route_id")
    assert plain == traced


def test_decisions_name_the_keywords_behind_target_phase_and_size(project):
    d = run("review a typo in the checklist", project, decisions=True)["decisions"]
    assert d["phase"] == {"target": "review", "from": "keywords", "keywords": ["review"]}
    assert d["size"] == {"size": "small", "from": "keywords", "keywords": ["typo"]}
    d = run("add an export endpoint", project, decisions=True)["decisions"]
    assert d["phase"] == {"target": "build", "from": "keywords", "keywords": ["add", "endpoint"]}
    assert d["size"] == {"size": "medium", "from": "default", "keywords": []}
    assert run("the orders thing", project, decisions=True)["decisions"]["phase"] == {"target": "build", "from": "guessed", "keywords": []}
    d = run("build a new platform", project, size="small", decisions=True)["decisions"]
    assert d["size"] == {"size": "small", "from": "given", "keywords": []}
