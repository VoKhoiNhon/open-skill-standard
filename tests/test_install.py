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


def test_symlink_install_links_to_the_source(reg, tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "src/my-skill", "my-skill")))
    p = install.plan(src, reg.agents["gemini-cli"], mode="symlink")
    install.apply(p)
    assert p.dest.is_symlink() and p.dest.resolve() == src.path
    [rec] = install.manifest()
    assert rec["mode"] == "symlink" and rec["files"] == {}
    assert install.plan(src, reg.agents["gemini-cli"], mode="symlink").action == "unchanged"


def _installed(reg, tmp_path, name="my-skill", agent="codex", **kw):
    src = install.resolve_source(str(skill(tmp_path / "src" / name, name)))
    (src.path / "notes.md").write_text("n\n")
    p = install.plan(src, reg.agents[agent], **kw)
    install.apply(p)
    return p


def test_remove_deletes_only_recorded_unchanged_files(reg, tmp_path):
    p = _installed(reg, tmp_path)
    (p.dest / "notes.md").write_text("my edit\n")  # the user changed a file
    (p.dest / "mine.txt").write_text("not from open-skill\n")  # and added one
    removed, kept = install.remove(p.dest)
    assert removed == ["SKILL.md"]
    assert set(kept) == {"notes.md", "mine.txt"}
    assert (p.dest / "notes.md").read_text() == "my edit\n" and (p.dest / "mine.txt").exists()
    assert install.manifest() == []


def test_remove_clears_empty_folders(reg, tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "src/deep", "deep")))
    (src.path / "sub/inner").mkdir(parents=True)
    (src.path / "sub/inner/x.md").write_text("x\n")
    p = install.plan(src, reg.agents["codex"])
    install.apply(p)
    removed, kept = install.remove(p.dest)
    assert set(removed) == {"SKILL.md", "sub/inner/x.md"} and kept == []
    assert not p.dest.exists() and p.dest.parent.is_dir()  # the agent's folder itself is kept


def test_remove_refuses_what_open_skill_did_not_install(reg, tmp_path):
    theirs = skill(tmp_path / "home/.agents/skills/open-skill-router", "open-skill-router")
    with pytest.raises(LookupError):
        install.remove(theirs)
    assert (theirs / "SKILL.md").exists()


def test_remove_dry_run_changes_nothing(reg, tmp_path):
    p = _installed(reg, tmp_path)
    removed, _ = install.remove(p.dest, dry_run=True)
    assert removed and (p.dest / "SKILL.md").exists() and len(install.manifest()) == 1


def test_remove_never_follows_a_link_out_of_the_skill(reg, tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "src/linked", "linked")))
    (src.path / "sub").mkdir()
    (src.path / "sub/x.md").write_text("x\n")
    p = install.plan(src, reg.agents["codex"])
    install.apply(p)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "x.md").write_text("x\n")  # same content as the recorded file
    import shutil
    shutil.rmtree(p.dest / "sub")
    (p.dest / "sub").symlink_to(elsewhere, target_is_directory=True)
    removed, _ = install.remove(p.dest)
    assert "sub/x.md" not in removed and (elsewhere / "x.md").exists()



def test_remove_symlink_install(reg, tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "src/linky", "linky")))
    p = install.plan(src, reg.agents["codex"], mode="symlink")
    install.apply(p)
    assert install.remove(p.dest) == (["linky"], [])
    assert not p.dest.is_symlink() and (src.path / "SKILL.md").exists()  # the link goes, its target stays


def test_repointed_symlink_is_kept(reg, tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "src/linky", "linky")))
    p = install.plan(src, reg.agents["codex"], mode="symlink")
    install.apply(p)
    p.dest.unlink()
    other = skill(tmp_path / "other/linky", "linky")
    p.dest.symlink_to(other, target_is_directory=True)  # the user pointed it elsewhere
    assert install.remove(p.dest) == ([], ["linky"])
    assert p.dest.is_symlink() and (other / "SKILL.md").exists()
