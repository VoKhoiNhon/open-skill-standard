"""Run evals/routing.yaml against the real registry with every skill installed."""

from pathlib import Path

import pytest
import yaml

from open_skill import registry, route
from open_skill.scan import Installed

ROOT = Path(__file__).parents[1]
REG = registry.load(ROOT)
ALL = [Installed(sid, sid.split("/", 1)[1], "/x", s.get("description", ""), False) for sid, s in REG.skills.items()]
CASES = yaml.safe_load((ROOT / "evals" / "routing.yaml").read_text())["cases"]


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_routing_case(case, tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    for f in case.get("files", []):
        (proj / f).parent.mkdir(parents=True, exist_ok=True)
        (proj / f).write_text("x")
    r = route.route(case["task"], proj, REG, ALL, role=case.get("role"), size=case.get("size"),
                    model=case.get("model"), record=False)
    ids = [s["id"] for s in r["chain"]]
    shown = " → ".join(f"{s['phase']}:{s['id']}" for s in r["chain"]) or r["advice"]
    for sid in case.get("include", []):
        assert sid in ids, f"{sid} missing from {shown}"
    for sid in case.get("exclude", []):
        assert sid not in ids, f"{sid} unexpectedly in {shown}"
    if "first" in case:
        assert ids and ids[0] == case["first"], shown
    if "phases" in case:
        assert [s["phase"] for s in r["chain"]] == case["phases"], shown
    if "advice" in case:
        assert r["advice"] == case["advice"], shown
    if "max_steps" in case:
        assert len(ids) <= case["max_steps"], shown
    if "last_phase" in case:
        assert r["chain"][-1]["phase"] == case["last_phase"], shown


def test_every_role_has_an_eval():
    assert {c["role"] for c in CASES} >= set(REG.roles)
