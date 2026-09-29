import re
from pathlib import Path

from open_skill import registry

REPO = Path(__file__).parents[1]


def _agent_rows(readme: str) -> dict[str, tuple[str, str]]:
    rows = re.findall(r"^\|[^|]+\| `([a-z0-9-]+)` \| `([^`]+)` \| `([^`]+)` \|$", readme, re.M)
    return {aid: (g, p) for aid, g, p in rows}


def test_readme_agent_table_matches_the_registry():
    reg = registry.load()
    want = {aid: (a["global"][0]["path"], a["project"][0]["path"]) for aid, a in reg.agents.items()}
    for name in ("README.md", "README.vi.md"):
        assert _agent_rows((REPO / name).read_text()) == want, f"{name}: update the agent table from registry/agents"


def test_router_skill_lists_the_taxonomy_phases_the_agent_passes():
    skill = (REPO / "skills" / "open-skill-router" / "SKILL.md").read_text()
    assert "--phase" in skill and "--size" in skill
    listed = set(re.findall(r"`([a-z]+)` \(", skill))
    assert {p["id"] for p in registry.load().taxonomy["phases"]} <= listed, "list every phase id in the router skill"


def test_router_manual_path_follows_the_playbooks_build_window():
    # The manual fallback walked plan → build → verify → review for every role; eleven roles set a build_window.
    skill = (REPO / "skills" / "open-skill-router" / "SKILL.md").read_text()
    manual = skill.split("## Without the CLI")[1]
    assert "Build tasks for this role walk" in manual and "done directly" in manual
