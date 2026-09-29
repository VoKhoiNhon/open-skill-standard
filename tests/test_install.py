from pathlib import Path

import pytest

from open_skill import install, registry

REPO = Path(__file__).parents[1]


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "osh"))


@pytest.fixture(scope="module")
def reg():
    return registry.load()


def skill(folder: Path, name: str, body: str = "Body.\n") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: A demo skill.\n---\n\n{body}")
    return folder


def test_core_skill_resolves_by_name():
    src = install.resolve_source("open-skill-router")
    assert src.kind == "core" and src.name == "open-skill-router"
    assert src.path == REPO / "skills" / "open-skill-router"


def test_local_folder_resolves_by_path(tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "my-skill", "my-skill")))
    assert src.kind == "local" and src.name == "my-skill" and src.path == (tmp_path / "my-skill").resolve()


def test_unknown_source_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="core skill"):
        install.resolve_source("no-such-skill")
    with pytest.raises(ValueError):
        install.resolve_source(str(tmp_path))  # a folder without SKILL.md


@pytest.mark.parametrize("bad", ["../escape", "Upper", "a/b", "-dash"])
def test_unsafe_skill_names_are_rejected(tmp_path, bad):
    with pytest.raises(ValueError, match="name"):
        install.resolve_source(str(skill(tmp_path / "s", bad)))


def test_plan_targets_the_agents_first_global_folder(reg, tmp_path):
    p = install.plan(install.resolve_source("open-skill-router"), reg.agents["codex"])
    assert p.dest == tmp_path / "home/.agents/skills/open-skill-router"
    assert (p.agent, p.scope, p.action) == ("codex", "global", "install")


def test_plan_in_a_project_targets_the_first_project_folder(reg, tmp_path):
    p = install.plan(install.resolve_source("open-skill-router"), reg.agents["claude-code"], project=tmp_path / "proj")
    assert p.dest == (tmp_path / "proj").resolve() / ".claude/skills/open-skill-router"
    assert p.scope == "project"


def test_agent_without_project_folders_cannot_install_in_a_project(tmp_path):
    agent = {"id": "solo", "global": [{"path": "~/.solo/skills"}]}
    with pytest.raises(ValueError, match="project"):
        install.plan(install.resolve_source("open-skill-router"), agent, project=tmp_path)
