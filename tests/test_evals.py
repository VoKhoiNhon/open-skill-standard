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
    (tmp_path / "bad.yaml").write_text("skill: x\nqueries:\n  - {q: hi, trigger: true, holdout: yes please}\n")
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


def test_lexical_report_splits_train_and_holdout():
    d = {"pdf-tools": "Extract text and tables from PDF files.", "sql-helper": "Write SQL queries for warehouses."}
    sets = {"pdf-tools": [{"q": "extract tables from this PDF", "trigger": True},
                          {"q": "pull the text out of report.pdf", "trigger": True, "holdout": True},
                          {"q": "write a SQL query for revenue", "trigger": False, "holdout": True}]}
    rep = evals.trigger_report_lexical(sets, d)["pdf-tools"]
    assert (rep["train"]["tp"], rep["train"]["fn"]) == (1, 0)
    assert (rep["validation"]["tp"], rep["validation"]["tn"]) == (1, 1)


# Regression floors for the lexical proxy, just under the current scores so losing one query fails:
# skill -> (precision, recall) on the tuning queries. Raise them when descriptions improve, never lower them silently.
TUNE_FLOORS = {
    "open-skill-intel": (0.75, 0.35),
    "open-skill-learn": (0.95, 0.75),
    "open-skill-router": (0.95, 0.55),
    "open-skill-standards": (0.95, 0.75),
}


# The same on the held-out queries, which are never used for tuning: a false alarm or a lost catch there means a
# description change did not generalize. Standards has one held-out false alarm today, hence precision 0.
HOLDOUT_FLOORS = {
    "open-skill-intel": (0.95, 0.0),
    "open-skill-learn": (0.95, 0.15),
    "open-skill-router": (0.95, 0.0),
    "open-skill-standards": (0.0, 0.0),
}


def _core_trigger_report():
    return evals.trigger_report_lexical(evals.load_trigger_sets(ROOT / "evals" / "triggers"),
                                        evals.skill_descriptions(REG, ROOT / "skills"))


def test_core_skills_trigger_proxy_meets_floor():
    rep = _core_trigger_report()
    assert set(rep) == set(TUNE_FLOORS)
    for skill, (precision, recall) in TUNE_FLOORS.items():
        m = rep[skill]["train"]
        assert m["precision"] >= precision and m["recall"] >= recall, (skill, m)


def test_core_skills_trigger_proxy_holds_on_holdout():
    rep = _core_trigger_report()
    assert set(rep) == set(HOLDOUT_FLOORS)
    for skill, (precision, recall) in HOLDOUT_FLOORS.items():
        m = rep[skill]["validation"]
        assert m["tp"] + m["fn"] >= 5 and m["tn"] + m["fp"] >= 5, (skill, "holdout too small")
        assert m["precision"] >= precision and m["recall"] >= recall, (skill, m)


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


def test_split_honors_holdout_flags():
    qs = [{"q": "a", "trigger": True}, {"q": "b", "trigger": True, "holdout": True},
          {"q": "c", "trigger": False, "holdout": False}, {"q": "d", "trigger": False, "holdout": True}]
    train, val = evals.split_queries(qs)
    assert [q["q"] for q in train] == ["a", "c"] and [q["q"] for q in val] == ["b", "d"]


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


def test_suggest_terms_finds_shared_words_of_missed_positives():
    labels = [{"q": "rotate the api keys for staging", "trigger": True},
              {"q": "rotate api keys before the audit", "trigger": True},
              {"q": "rotate the logo image", "trigger": False},
              {"q": "store secrets in the vault", "trigger": True},
              {"q": "list vault audit logs", "trigger": False}]
    fired = [False, False, False, True, True]
    s = evals.suggest_terms(labels, fired, "Store secrets in a vault. Use for secrets and vault questions.")
    assert s["add"][:2] == [("api", 2), ("api keys", 2)]  # shared by both misses, absent from the description
    assert "rotate" not in dict(s["add"])  # also in a near miss, so adding it would cause false alarms
    assert "audit" not in dict(s["add"])
    assert s["false_alarms"] == [("vault", 1)]  # the description word that matched the near miss


def test_lexical_report_suggestions_use_tuning_queries_only():
    d = {"pdf-tools": "Extract text from PDF files.", "sql-helper": "Write SQL queries for warehouses."}
    sets = {"pdf-tools": [{"q": "merge scanned invoices", "trigger": True}, {"q": "merge scanned receipts", "trigger": True},
                          {"q": "split scanned contracts", "trigger": True, "holdout": True},
                          {"q": "split scanned forms", "trigger": True, "holdout": True}]}
    rep = evals.trigger_report_lexical(sets, d, suggest=True)["pdf-tools"]
    assert rep["suggest"]["add"] == [("merge", 2), ("merge scanned", 2), ("scanned", 2)]
    assert "suggest" not in evals.trigger_report_lexical(sets, d)["pdf-tools"]


def test_case_can_give_the_phase_an_agent_would_pass():
    case = {"role": "backend-developer", "task": "customers say invoice export returns nothing since yesterday",
            "first": "superpowers/systematic-debugging"}
    assert evals.run_case({**case, "phase": "operate"}, REG, ALL) == []


def test_first_phase_and_include_any_assertions():
    case = {"role": "backend-developer", "task": "the export endpoint is failing with a 500 error"}
    assert evals.run_case({**case, "first_phase": "operate",
                           "include_any": ["superpowers/systematic-debugging", "nope/nope"]}, REG, ALL) == []
    fails = evals.run_case({**case, "first_phase": "plan", "include_any": ["nope/a", "nope/b"]}, REG, ALL)
    assert any("first phase should be plan" in f for f in fails) and any("one of nope/a, nope/b" in f for f in fails)
