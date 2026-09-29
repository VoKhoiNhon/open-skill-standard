"""Each bundled adapter's detect rules against the folders its installers really create (tests/fixtures/layouts).

Claude Code plugins land in ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/ with the plugin's whole source
folder copied (the marketplace names come from each upstream .claude-plugin/marketplace.json); the skills CLI
installs into each agent's skill folder under the skill's `name`; spec-kit writes speckit-<command> into the project
skill folder of the chosen integration; the Claude desktop app keeps skills under local-agent-mode-sessions/.
"""

from pathlib import Path

import pytest

from open_skill import registry, scan

LAYOUTS = Path(__file__).parent / "fixtures" / "layouts"
REG = registry.load()


@pytest.fixture(scope="module")
def found():
    mp = pytest.MonkeyPatch()
    mp.setenv("HOME", str(LAYOUTS / "home"))
    mp.delenv("CLAUDECODE", raising=False)
    try:
        yield {i.id: i for i in scan.scan(REG, LAYOUTS / "project")}
    finally:
        mp.undo()


CASES = [
    ("superpowers/brainstorming", "claude-code", "superpowers:brainstorming"),
    ("addy-agent-skills/spec-driven-development", "claude-code", "agent-skills:spec-driven-development"),
    ("anthropic-skills/xlsx", "claude-code", "document-skills:xlsx"),
    ("anthropic-skills/docx", "claude-code", "anthropic-skills:docx"),
    ("bmad-method/bmad-build", "claude-code", "bmad-method:bmad-build"),
    ("bmad-method/bmad-forge-idea", "claude-code", "bmad-toolbox:bmad-forge-idea"),
    ("context7/context7-mcp", "claude-code", "context7:context7-mcp"),
    ("knowledge-work-data/validate-data", "claude-code", "data:validate-data"),
    ("knowledge-work-data/explore-data", "claude-code", "data:explore-data"),
    ("knowledge-work-engineering/debug", "claude-code", "engineering:debug"),
    ("knowledge-work-design/ux-copy", "claude-code", "design:ux-copy"),
    ("knowledge-work-product-management/write-spec", "claude-code", "product-management:write-spec"),
    ("ponytail/ponytail-review", "claude-code", "ponytail:ponytail-review"),
    ("taste-skill/redesign-skill", "claude-code", "taste-skill:redesign-skill"),
    ("open-skill/open-skill-router", "claude-code", "open-skill:open-skill-router"),
    ("vercel-agent-skills/react-best-practices", "codex", "vercel-react-best-practices"),
    ("vercel-agent-skills/deploy-to-vercel", "claude-code", "deploy-to-vercel"),
    ("spec-kit/plan", "claude-code", "speckit-plan"),
    ("spec-kit/implement", "codex", "speckit-implement"),
    ("spec-kit/specify", "github-copilot", "speckit-specify"),
]


@pytest.mark.parametrize("sid,agent,invoke", CASES)
def test_adapter_finds_its_skill_in_the_real_layout(found, sid, agent, invoke):
    assert sid in found, f"{sid} not detected"
    assert found[sid].agents.get(agent) == invoke and not found[sid].inferred


def test_every_adapter_with_detect_rules_has_a_layout_case():
    assert {src for src, a in REG.adapters.items() if a.get("detect")} <= {sid.split("/")[0] for sid, _, _ in CASES}
