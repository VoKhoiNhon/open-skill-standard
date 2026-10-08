import os
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
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: A demo skill.\n---\n\n{body}", encoding="utf-8")
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
    (src.path / "references/a.md").write_text("ref\n", encoding="utf-8")
    p = install.plan(src, reg.agents["codex"])
    install.apply(p)
    assert (p.dest / "SKILL.md").read_bytes() == (src.path / "SKILL.md").read_bytes()
    assert (p.dest / "references/a.md").read_text(encoding="utf-8") == "ref\n"
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


@pytest.mark.symlinks
def test_broken_link_at_the_target_is_refused(reg, tmp_path):
    target = tmp_path / "home/.agents/skills/open-skill-router"
    target.parent.mkdir(parents=True)
    target.symlink_to(tmp_path / "gone")
    assert install.plan(install.resolve_source("open-skill-router"), reg.agents["codex"]).action == "refuse"


@pytest.mark.symlinks
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
    (src.path / "notes.md").write_text("n\n", encoding="utf-8")
    p = install.plan(src, reg.agents[agent], **kw)
    install.apply(p)
    return p


def test_remove_deletes_only_recorded_unchanged_files(reg, tmp_path):
    p = _installed(reg, tmp_path)
    (p.dest / "notes.md").write_text("my edit\n", encoding="utf-8")  # the user changed a file
    (p.dest / "mine.txt").write_text("not from open-skill\n", encoding="utf-8")  # and added one
    removed, kept = install.remove(p.dest)
    assert removed == ["SKILL.md"]
    assert set(kept) == {"notes.md", "mine.txt"}
    assert (p.dest / "notes.md").read_text(encoding="utf-8") == "my edit\n" and (p.dest / "mine.txt").exists()
    assert install.manifest() == []


def test_remove_clears_empty_folders(reg, tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "src/deep", "deep")))
    (src.path / "sub/inner").mkdir(parents=True)
    (src.path / "sub/inner/x.md").write_text("x\n", encoding="utf-8")
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


@pytest.mark.symlinks
def test_remove_never_follows_a_link_out_of_the_skill(reg, tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "src/linked", "linked")))
    (src.path / "sub").mkdir()
    (src.path / "sub/x.md").write_text("x\n", encoding="utf-8")
    p = install.plan(src, reg.agents["codex"])
    install.apply(p)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "x.md").write_text("x\n", encoding="utf-8")  # same content as the recorded file
    import shutil
    shutil.rmtree(p.dest / "sub")
    (p.dest / "sub").symlink_to(elsewhere, target_is_directory=True)
    removed, _ = install.remove(p.dest)
    assert "sub/x.md" not in removed and (elsewhere / "x.md").exists()



@pytest.mark.symlinks
def test_remove_symlink_install(reg, tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "src/linky", "linky")))
    p = install.plan(src, reg.agents["codex"], mode="symlink")
    install.apply(p)
    assert install.remove(p.dest) == (["linky"], [])
    assert not p.dest.is_symlink() and (src.path / "SKILL.md").exists()  # the link goes, its target stays


@pytest.mark.symlinks
def test_repointed_symlink_is_kept(reg, tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "src/linky", "linky")))
    p = install.plan(src, reg.agents["codex"], mode="symlink")
    install.apply(p)
    p.dest.unlink()
    other = skill(tmp_path / "other/linky", "linky")
    p.dest.symlink_to(other, target_is_directory=True)  # the user pointed it elsewhere
    assert install.remove(p.dest) == ([], ["linky"])
    assert p.dest.is_symlink() and (other / "SKILL.md").exists()


def _old_core_install(reg, tmp_path, text="old wording\n"):
    """A core skill installed by an older open-skill: different content, recorded with an older version."""
    p = install.plan(install.resolve_source("open-skill-router"), reg.agents["codex"])
    install.apply(p)
    import shutil
    shutil.rmtree(p.dest)
    skill(p.dest, "open-skill-router", text)
    [rec] = install.manifest()
    rec["files"], rec["version"] = install._files(p.dest), "0.0.1"
    install._save([rec])
    return p.dest


def test_update_reinstalls_core_skills_at_the_cli_version(reg, tmp_path):
    from open_skill import __version__
    dest = _old_core_install(reg, tmp_path)
    msgs = install.update()
    assert msgs[0].startswith("updated open-skill-router for codex")
    assert install._files(dest) == install._files(REPO / "skills/open-skill-router")
    [rec] = install.manifest()
    assert rec["version"] == __version__ and rec["files"] == install._files(dest)
    assert install.update()[0].startswith("up to date")
    assert not [x for x in dest.parent.iterdir() if x.name.startswith(".")]


def test_update_skips_a_skill_the_user_changed(reg, tmp_path):
    dest = _old_core_install(reg, tmp_path)
    (dest / "SKILL.md").write_text("my own edit\n", encoding="utf-8")
    assert "you changed it" in install.update()[0]
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "my own edit\n"
    assert install.manifest()[0]["version"] == "0.0.1"


def test_update_dry_run_and_agent_filter_change_nothing(reg, tmp_path):
    dest = _old_core_install(reg, tmp_path)
    assert install.update(dry_run=True)[0].startswith("would update")
    assert install.update(agent="cursor") == []
    assert "old wording" in (dest / "SKILL.md").read_text(encoding="utf-8")


def test_update_leaves_local_skills_to_the_user(reg, tmp_path):
    p = _installed(reg, tmp_path)
    assert "local skill" in install.update()[0]
    assert (p.dest / "notes.md").exists()


@pytest.mark.symlinks
def test_update_relinks_a_core_symlink_to_this_cli(reg, tmp_path):
    import shutil
    old = tmp_path / "old-cli/skills/open-skill-router"
    shutil.copytree(REPO / "skills/open-skill-router", old)
    dest = tmp_path / "home/.agents/skills/open-skill-router"
    dest.parent.mkdir(parents=True)
    dest.symlink_to(old, target_is_directory=True)
    install._save([{"skill": "open-skill-router", "agent": "codex", "scope": "global", "dest": str(dest),
                    "source": str(old), "kind": "core", "mode": "symlink", "version": "0.0.1", "files": {}}])
    assert install.update()[0].startswith("updated")
    assert install.link_target(dest) == str(REPO / "skills/open-skill-router")
    assert old.is_dir()  # the old target is not ours to delete


@pytest.mark.parametrize("name", ["synced", "anthropic-skills"])
def test_folder_claude_code_skips_is_refused(reg, tmp_path, name):
    src = install.resolve_source(str(skill(tmp_path / name, name)))
    p = install.plan(src, reg.agents["claude-code"])
    assert p.action == "refuse" and "does not load" in p.reason
    assert install.plan(src, reg.agents["codex"]).action == "install"  # only Claude Code reserves the name


class PrivilegeNotHeld(PermissionError):
    winerror = 1314  # what Windows raises when the user may not create symbolic links


def _refuse_links(monkeypatch, error=PrivilegeNotHeld):
    def refuse(*a, **k):
        raise error(1, "A required privilege is not held by the client")
    monkeypatch.setattr(install.os, "symlink", refuse)


def test_a_refused_symlink_install_says_how_to_proceed(reg, tmp_path, monkeypatch):
    src = install.resolve_source(str(skill(tmp_path / "src" / "demo", "demo")))
    p = install.plan(src, reg.agents["codex"], mode="symlink")
    _refuse_links(monkeypatch)
    with pytest.raises(OSError) as e:
        install.apply(p)
    assert "--symlink" in e.value.strerror and "Developer Mode" in e.value.strerror
    assert not p.dest.exists() and install.manifest() == []


@pytest.mark.symlinks
def test_a_refused_relink_keeps_the_old_link(reg, tmp_path, monkeypatch):
    import shutil
    old = tmp_path / "old-cli/skills/open-skill-router"
    shutil.copytree(REPO / "skills/open-skill-router", old)
    dest = tmp_path / "home/.agents/skills/open-skill-router"
    dest.parent.mkdir(parents=True)
    dest.symlink_to(old, target_is_directory=True)
    install._save([{"skill": "open-skill-router", "agent": "codex", "scope": "global", "dest": str(dest),
                    "source": str(old), "kind": "core", "mode": "symlink", "version": "0.0.1", "files": {}}])
    _refuse_links(monkeypatch)
    with pytest.raises(OSError):
        install.update()
    assert dest.is_symlink() and install.link_target(dest) == str(old)


def test_other_symlink_errors_keep_their_own_wording(reg, tmp_path, monkeypatch):
    src = install.resolve_source(str(skill(tmp_path / "src" / "demo", "demo")))
    p = install.plan(src, reg.agents["codex"], mode="symlink")
    _refuse_links(monkeypatch, PermissionError)  # e.g. EACCES on a folder this user cannot write
    with pytest.raises(PermissionError) as e:
        install.apply(p)
    assert "Developer Mode" not in str(e.value)


@pytest.mark.symlinks
def test_a_failed_relink_keeps_the_old_link_and_no_second_one(reg, tmp_path, monkeypatch):
    import shutil
    old = tmp_path / "old-cli/skills/open-skill-router"
    shutil.copytree(REPO / "skills/open-skill-router", old)
    dest = tmp_path / "home/.agents/skills/open-skill-router"
    dest.parent.mkdir(parents=True)
    dest.symlink_to(old, target_is_directory=True)
    install._save([{"skill": "open-skill-router", "agent": "codex", "scope": "global", "dest": str(dest),
                    "source": str(old), "kind": "core", "mode": "symlink", "version": "0.0.1", "files": {}}])

    def fail(self, target):
        raise OSError(16, "Device or resource busy")
    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises(OSError):
        install.update()
    assert [x.name for x in dest.parent.iterdir()] == ["open-skill-router"]
    assert install.link_target(dest) == str(old)  # the old link is back


@pytest.mark.parametrize("raw,want", [
    ("\\\\?\\C:\\Users\\me\\skills\\demo", "C:\\Users\\me\\skills\\demo"),
    ("\\\\?\\UNC\\server\\share\\demo", "\\\\server\\share\\demo"),
    ("/home/me/skills/demo", "/home/me/skills/demo"),
    ("relative\\demo", "relative\\demo"),
])
def test_link_target_drops_the_windows_long_path_prefix(monkeypatch, raw, want):
    # On Windows os.readlink returns a link's substitute name, \\?\C:\..., not the path it was made with, so an
    # install recorded as C:\... never matched its own link and remove and update left it alone.
    monkeypatch.setattr(install.os, "readlink", lambda p: raw)
    assert install.link_target(Path("x")) == want
