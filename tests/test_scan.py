from pathlib import Path

import pytest

from open_skill import registry, scan

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def reg():
    return registry.load(FIX / "repo")


@pytest.fixture(autouse=True)
def fake_home(monkeypatch):
    monkeypatch.setenv("HOME", str(FIX / "home"))


def by_invoke(items):
    return {i.invoke: i for i in items}


def test_plugin_rule_wins_over_later_rule(reg):
    got = by_invoke(scan.scan(reg))
    tdd = got["superpowers:test-driven-development"]
    assert tdd.id == "superpowers/test-driven-development"
    assert tdd.inferred is False
    assert "test-driven-development" not in got  # same skill, first rule wins


def test_unknown_upstream_skill_is_inferred(reg):
    got = by_invoke(scan.scan(reg))
    assert got["superpowers:brand-new-skill"].inferred is True
    assert got["superpowers:brand-new-skill"].id == "superpowers/brand-new-skill"


def test_skill_outside_any_adapter_is_harvested(reg):
    got = by_invoke(scan.scan(reg))
    mine = got["my-internal-skill"]
    assert mine.id == "harvested/my-internal-skill"
    assert mine.inferred is True
    assert "warehouse" in mine.description
    assert got["toolkit:lint-helper"].id == "harvested/lint-helper"


def test_project_skills_need_project(reg):
    assert "speckit-plan" not in by_invoke(scan.scan(reg))
    got = by_invoke(scan.scan(reg, project=FIX / "project"))
    assert got["speckit-plan"].id == "spec-kit/plan"
    assert got["speckit-plan"].inferred is False


def test_builtin_adapter_available_only_under_its_env(reg, monkeypatch):
    monkeypatch.delenv("CLAUDECODE", raising=False)
    assert "code-review" not in by_invoke(scan.scan(reg))
    monkeypatch.setenv("CLAUDECODE", "1")
    got = by_invoke(scan.scan(reg))
    assert got["code-review"].id == "claude-code-builtin/code-review" and got["code-review"].inferred is False


def test_claude_code_rules_tag_the_agent(reg):
    tdd = by_invoke(scan.scan(reg))["superpowers:test-driven-development"]
    assert tdd.agent == "claude-code"
    assert tdd.agents["claude-code"] == "superpowers:test-driven-development"


def test_rule_may_name_its_agent(reg, tmp_path, monkeypatch):
    skill = tmp_path / ".demo/skills/brainstorming/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: brainstorming\ndescription: d\n---\n")
    monkeypatch.setenv("HOME", str(tmp_path))
    reg.adapters["superpowers"]["detect"] = [{"glob": "~/.demo/skills/{name}/SKILL.md", "invoke": "{name}", "agent": "demo-agent"}]
    got = by_invoke(scan.scan(reg))["brainstorming"]
    assert got.agent == "demo-agent" and got.agents == {"demo-agent": "brainstorming"}


def test_same_skill_in_two_agents_is_listed_once(reg):
    items = [i for i in scan.scan(reg) if i.id == "superpowers/test-driven-development"]
    assert len(items) == 1
    tdd = items[0]
    assert tdd.agent == "claude-code" and tdd.invoke == "superpowers:test-driven-development"
    assert tdd.agents == {"claude-code": "superpowers:test-driven-development", "codex": "test-driven-development"}


def test_project_skills_placeholder_covers_other_agents(reg):
    got = by_invoke(scan.scan(reg, project=FIX / "project"))
    assert got["speckit-tasks"].id == "spec-kit/tasks" and got["speckit-tasks"].agent == "codex"
    assert got["speckit-plan"].agents == {"claude-code": "speckit-plan"}


def test_relocated_agent_home_is_scanned(reg, tmp_path, monkeypatch):
    skill = tmp_path / "codex-home/skills/brainstorming/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: brainstorming\ndescription: d\n---\n")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    got = by_invoke(scan.scan(reg))["brainstorming"]
    assert got.id == "superpowers/brainstorming" and got.agents == {"codex": "brainstorming"}


def test_shared_folder_is_seen_by_every_agent_that_reads_it(reg):
    helper = by_invoke(scan.scan(reg))["shared-helper"]
    assert helper.agent == "codex"  # ~/.agents/skills is codex's first folder, demo-agent's second
    assert helper.agents == {"codex": "shared-helper", "demo-agent": "shared-helper"}


def test_bundled_adapters_find_their_skills_in_other_agents(tmp_path, monkeypatch):
    for folder in (".agents/skills", ".cursor/skills"):
        skill = tmp_path / folder / "open-skill-router/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: open-skill-router\ndescription: d\n---\n")
    proj = tmp_path / "proj"
    (proj / ".agents/skills/speckit-plan").mkdir(parents=True)
    (proj / ".agents/skills/speckit-plan/SKILL.md").write_text("---\nname: speckit-plan\ndescription: d\n---\n")
    monkeypatch.setenv("HOME", str(tmp_path))
    got = {i.id: i for i in scan.scan(registry.load(), proj)}
    router = got["open-skill/open-skill-router"]
    assert {"codex", "cursor", "gemini-cli", "github-copilot"} <= set(router.agents)
    assert "claude-code" not in router.agents
    assert "codex" in got["spec-kit/plan"].agents


def test_agent_view_keeps_only_its_skills_with_its_names(reg):
    got = by_invoke(scan.scan(reg, agent="codex"))
    assert got["test-driven-development"].id == "superpowers/test-driven-development"
    assert got["test-driven-development"].agent == "codex"
    assert "superpowers:test-driven-development" not in got  # plugin names are Claude Code only
    assert "my-internal-skill" not in got  # lives in ~/.claude/skills, which codex does not read


def test_later_rule_of_same_adapter_does_not_reclaim_a_path(reg, tmp_path, monkeypatch):
    # Upstream folder "react-best-practices" installs as "vendor-react-best-practices"; "vendor-cli" keeps its name.
    monkeypatch.setenv("HOME", str(tmp_path))
    for folder in ("vendor-react-best-practices", "vendor-cli"):
        (tmp_path / ".claude/skills" / folder).mkdir(parents=True)
        (tmp_path / ".claude/skills" / folder / "SKILL.md").write_text(f"---\nname: {folder}\ndescription: d\n---\n")
    reg.adapters["vendor"] = {"source": "vendor", "skills": [{"name": "react-best-practices"}, {"name": "vendor-cli"}],
                              "detect": [{"glob": "~/.claude/skills/{name}/SKILL.md", "invoke": "{name}"},
                                         {"glob": "~/.claude/skills/vendor-{name}/SKILL.md", "invoke": "vendor-{name}"}]}
    ids = sorted(i.id for i in scan.scan(reg) if i.id.startswith("vendor/"))
    assert ids == ["vendor/react-best-practices", "vendor/vendor-cli"]  # not also an inferred "vendor/cli"


def test_describe_ignores_non_string_frontmatter(tmp_path):
    # An installed skill is untrusted text; str() of a YAML alias tree can be enormous, and ~ used to read as "None".
    from open_skill import scan

    bomb = "\n".join(["a0: &a0 [x, x, x, x, x, x, x, x, x, x]"] + [
        f"a{i}: &a{i} [" + ", ".join([f"*a{i-1}"] * 10) + "]" for i in range(1, 8)]).replace("a7:", "description:")
    (tmp_path / "odd").mkdir()
    (tmp_path / "odd" / "SKILL.md").write_text(f"---\nname: ~\n{bomb}\n---\nbody")
    assert scan._describe(tmp_path / "odd" / "SKILL.md") == ("odd", "")


def test_skill_installed_under_its_frontmatter_name_maps_to_its_registry_id(tmp_path, monkeypatch):
    # `npx skills add` names the folder after the frontmatter `name`, not the upstream folder "taste-skill".
    skill = tmp_path / ".claude/skills/design-taste-frontend/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: design-taste-frontend\ndescription: d\n---\n")
    monkeypatch.setenv("HOME", str(tmp_path))
    got = by_invoke(scan.scan(registry.load()))["design-taste-frontend"]
    assert got.id == "taste-skill/taste-skill" and got.inferred is False
