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


def test_copy_install_writes_files_and_records_them(reg, tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "src/my-skill", "my-skill")))
    (src.path / "references").mkdir()
    (src.path / "references/a.md").write_text("ref\n")
    p = install.plan(src, reg.agents["codex"])
    install.apply(p)
    assert (p.dest / "SKILL.md").read_bytes() == (src.path / "SKILL.md").read_bytes()
    assert (p.dest / "references/a.md").read_text() == "ref\n"
    [rec] = install.manifest()
    assert rec["skill"] == "my-skill" and rec["agent"] == "codex" and rec["dest"] == str(p.dest)
    assert rec["kind"] == "local" and rec["mode"] == "copy" and rec["source"] == str(src.path)
    assert set(rec["files"]) == {"SKILL.md", "references/a.md"}
    from open_skill import __version__
    assert rec["version"] == __version__
    assert not [x for x in p.dest.parent.iterdir() if x.name.startswith(".")]  # no temp folder left behind


def test_manifest_lives_in_the_user_layer(reg, tmp_path):
    install.apply(install.plan(install.resolve_source("open-skill-learn"), reg.agents["codex"]))
    assert (tmp_path / "osh" / "installed.json").is_file()


def test_different_existing_skill_is_never_overwritten(reg, tmp_path):
    theirs = skill(tmp_path / "home/.agents/skills/open-skill-router", "open-skill-router", "Someone else's.\n")
    before = (theirs / "SKILL.md").read_bytes()
    p = install.plan(install.resolve_source("open-skill-router"), reg.agents["codex"])
    assert p.action == "refuse" and "never overwrites" in p.reason
    install.apply(p)
    assert (theirs / "SKILL.md").read_bytes() == before and install.manifest() == []


def test_identical_existing_skill_is_left_alone_and_not_claimed(reg, tmp_path):
    import shutil
    dest = tmp_path / "home/.agents/skills/open-skill-router"
    shutil.copytree(REPO / "skills/open-skill-router", dest)
    p = install.plan(install.resolve_source("open-skill-router"), reg.agents["codex"])
    assert p.action == "unchanged"
    install.apply(p)
    assert install.manifest() == []  # open-skill did not create it, so it will never remove it


def test_broken_link_at_the_target_is_refused(reg, tmp_path):
    target = tmp_path / "home/.agents/skills/open-skill-router"
    target.parent.mkdir(parents=True)
    target.symlink_to(tmp_path / "gone")
    assert install.plan(install.resolve_source("open-skill-router"), reg.agents["codex"]).action == "refuse"
