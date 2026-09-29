"""Run evals/routing.yaml against the real registry with every skill installed."""

from pathlib import Path

import pytest

from open_skill import evals, registry

ROOT = Path(__file__).parents[1]
REG = registry.load(ROOT)
ALL = evals.all_installed(REG)
CASES = evals.load_routing_cases(ROOT / "evals" / "routing.yaml")


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_routing_case(case):
    assert evals.run_case(case, REG, ALL) == []


def test_every_role_has_an_eval():
    assert {c["role"] for c in CASES} >= set(REG.roles)


def test_failures_are_described():
    fails = evals.run_case({"task": "fix typo in README", "role": "fullstack-developer",
                            "include": ["superpowers/writing-plans"], "advice": "plan first"}, REG, ALL)
    assert any("missing" in f for f in fails) and any("advice should be" in f for f in fails)


def test_routing_report_counts_by_role():
    cases = [CASES[0], {"id": "broken", "role": "qa-engineer", "task": "fix typo in README", "advice": "nope"}]
    rep = evals.routing_report(cases, REG, ALL)
    assert rep["cases"] == 2 and rep["passed"] == 1 and rep["pass_rate"] == 0.5
    assert rep["by_role"]["qa-engineer"] == {"cases": 1, "passed": 0}
    assert next(r for r in rep["results"] if r["id"] == "broken")["failures"]


def test_load_trigger_sets(tmp_path):
    sets = evals.load_trigger_sets(ROOT / "tests" / "fixtures" / "triggers")
    assert sets == {"demo-skill": [{"q": "do the demo thing", "trigger": True}, {"q": "something unrelated", "trigger": False}]}
    (tmp_path / "bad.yaml").write_text("skill: x\nqueries:\n  - {q: hi}\n")
    with pytest.raises(ValueError):
        evals.load_trigger_sets(tmp_path)


def test_trigger_metrics():
    labels = [{"q": "a", "trigger": True}, {"q": "b", "trigger": True}, {"q": "c", "trigger": False}, {"q": "d", "trigger": False}]
    m = evals.trigger_metrics(labels, [True, False, True, False])
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (1, 1, 1, 1)
    assert m["precision"] == 0.5 and m["recall"] == 0.5 and m["missed"] == ["b"] and m["false_alarms"] == ["c"]


def test_lexical_triggers_prefers_the_matching_description():
    d = {"pdf-tools": "Extract text and tables from PDF files and fill PDF forms.",
         "sql-helper": "Write and optimize SQL queries for warehouses."}
    assert evals.lexical_triggers("fill this PDF form for me", d) == ["pdf-tools"]
    assert evals.lexical_triggers("the and of", d) == []


def test_core_skills_trigger_proxy_meets_floor():
    rep = evals.trigger_report_lexical(evals.load_trigger_sets(ROOT / "evals" / "triggers"),
                                       evals.skill_descriptions(REG, ROOT / "skills"))
    assert set(rep) == {"open-skill-router", "open-skill-standards", "open-skill-intel", "open-skill-learn"}
    # Regression floors for the lexical proxy; raise them when descriptions improve, never lower them silently.
    for skill, m in rep.items():
        assert m["precision"] >= 0.75, (skill, m)
        assert m["recall"] >= 0.4, (skill, m)


def test_invoked_skills_parses_stream_json():
    import json
    lines = [
        json.dumps({"type": "system", "subtype": "init"}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Routing."},
            {"type": "tool_use", "name": "Skill", "input": {"skill": "open-skill:open-skill-router"}},
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}),
        "not json",
    ]
    assert evals.invoked_skills("\n".join(lines)) == {"open-skill-router"}


def test_split_is_stable_and_stratified():
    qs = [{"q": f"p{i}", "trigger": True} for i in range(10)] + [{"q": f"n{i}", "trigger": False} for i in range(10)]
    train, val = evals.split_queries(qs)
    assert len(train) == 12 and len(val) == 8
    assert sum(q["trigger"] for q in train) == 6 and evals.split_queries(qs) == (train, val)


def test_agent_report_uses_rates_and_threshold():
    sets = {"s": [{"q": "yes", "trigger": True}, {"q": "no", "trigger": False}, {"q": "flaky", "trigger": True}]}
    calls = {"flaky": 0}

    def runner(q):
        if q == "flaky":
            calls["flaky"] += 1
            return {"s"} if calls["flaky"] == 1 else set()  # fires 1 of 3 times: below 0.5
        return {"s"} if q == "yes" else set()

    rep = evals.trigger_report_agent(sets, runner, runs=3)
    assert rep["s"]["rates"] == {"yes": 1.0, "no": 0.0, "flaky": 1 / 3}
    both = rep["s"]["train"]["tp"] + rep["s"]["validation"]["tp"]
    assert both == 1
