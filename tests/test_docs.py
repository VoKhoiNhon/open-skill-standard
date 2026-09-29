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
