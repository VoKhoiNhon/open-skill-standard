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
