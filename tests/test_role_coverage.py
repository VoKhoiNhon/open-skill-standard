"""Every role pack is exercised by the tuned routing evals: enough cases, several phases, every primary placed."""

from pathlib import Path

import pytest

from open_skill import evals, registry

ROOT = Path(__file__).parents[1]
REG = registry.load(ROOT)
CASES = evals.load_routing_cases(ROOT / "evals" / "routing.yaml")
MIN_CASES, MIN_PHASES = 5, 3


@pytest.fixture(scope="module")
def routes(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setenv("OPEN_SKILL_HOME", str(tmp_path_factory.mktemp("h")))
    try:
        installed = evals.all_installed(REG)
        yield [(c, evals.route_case(c, REG, installed)) for c in CASES]
    finally:
        mp.undo()


@pytest.mark.parametrize("rid", sorted(REG.roles))
def test_every_role_has_cases_across_phases(routes, rid):
    mine = [r for c, r in routes if c["role"] == rid]
    phases = {r["target_phase"] for r in mine}
    assert len(mine) >= MIN_CASES and len(phases) >= MIN_PHASES, f"{rid}: {len(mine)} cases, phases {sorted(phases)}"


def test_every_primary_skill_is_exercised(routes):
    # A primary counts when some case places it, or places a skill that names it as an interchangeable
    # alternative (anthropic-skills/claude-api only wins where the Claude Code built-in is not installed).
    placed = {s["id"] for _, r in routes for s in r["chain"]}
    placed |= {alt for sid in placed for alt in REG.skills.get(sid, {}).get("alternatives", [])}
    primaries = {sid for r in REG.roles.values() for e in (r.get("phases") or {}).values() for sid in e.get("primary", [])}
    assert not sorted(primaries - placed), "add a routing case that places each of these"
