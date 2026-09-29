"""Corrupt and partial user data, hostile filesystems and scale: the CLI must fail clearly and never lose notes."""

import errno
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from open_skill import cli, knowledge, userdata

REPO = Path(__file__).parents[1]


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "h"
    monkeypatch.setenv("OPEN_SKILL_HOME", str(h))
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    monkeypatch.delenv("CLAUDECODE", raising=False)
    return h


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_truncated_events_log_is_read_up_to_the_damage(home, capsys):
    # A crash or a full disk mid-append leaves half a JSON line; every route used to fail on JSONDecodeError.
    knowledge.record({"type": "proposed", "route_id": "r-1", "task": "t", "chain": [{"id": "s/a", "invoke": "a"}]})
    knowledge.record({"type": "feedback", "route_id": "r-1", "ran": ["a"], "outcome": "ok"})
    with (home / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write('{"type": "proposed", "route_id": "r-2", "ta')
    assert knowledge.personal_weights()["s/a"] > 0
    assert cli.main(["route", "add tests", "--project", str(home.parent)]) == 0
    rid = json.loads(capsys.readouterr().out)["route_id"]
    assert knowledge.route_recorded(rid)  # the next event starts on its own line, not glued to the broken one
    lines = (home / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4 and all(lines)
    assert '"route_id": "r-2", "ta' in (home / "events.jsonl").read_text(encoding="utf-8")  # damage kept, not rewritten


@pytest.mark.parametrize("text", ["roles: {data-engineer: 1.0\n", "- just\n- a list\n"])
def test_broken_profile_is_reported_and_left_alone(home, capsys, text):
    # Every command used to die with a yaml traceback (or AttributeError for a list), since all of them read it.
    home.mkdir()
    (home / "profile.yaml").write_text(text, encoding="utf-8")
    assert cli.main(["validate"]) == 2
    err = capsys.readouterr().err
    assert "profile.yaml" in err and "Traceback" not in err
    assert cli.main(["init", "--role", "data-engineer"]) == 2
    assert (home / "profile.yaml").read_text(encoding="utf-8") == text


def test_a_note_with_broken_frontmatter_does_not_block_migration_or_seed_sync(home):
    # yaml.safe_load raised inside the v0 -> v1 step and in seed sync, so every write failed from then on.
    k = home / "knowledge"
    k.mkdir(parents=True)
    broken = "---\nid: k-broken\napplies_to: [role:*\n---\nMy text.\n"
    (k / "k-broken.md").write_text(broken, encoding="utf-8")
    (k / "k-ok.md").write_text("---\nid: k-ok\ntype: lesson\napplies_to: ['role:*']\nsource: user\n---\nFine.\n",
                               encoding="utf-8")
    actions = userdata.migrate(home)
    assert any("k-broken.md" in a and "left as is" in a for a in actions)
    assert (k / "k-broken.md").read_text(encoding="utf-8") == broken
    assert userdata.data_version(home) == userdata.SCHEMA_VERSION
    assert knowledge.sync_seeds(["data-engineer"], {"data-engineer": [{"id": "x", "text": "Seed."}]}) == [
        "added data-engineer/x"]


def test_notes_path_that_is_a_file_stops_writes_before_anything_changes(home, tmp_path, capsys):
    # `learn` crashed with FileExistsError after already migrating and backing up; export exported nothing.
    home.mkdir()
    (home / "knowledge").write_text("my stuff\n", encoding="utf-8")
    assert cli.main(["learn", "Hello.", "--applies-to", "role:*"]) == 2
    assert cli.main(["export", str(tmp_path / "e.zip")]) == 2
    assert "not a folder" in capsys.readouterr().err
    assert sorted(p.name for p in home.iterdir()) == ["knowledge"]
    assert (home / "knowledge").read_text(encoding="utf-8") == "my stuff\n"


posix_perms = pytest.mark.skipif(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                                 reason="needs POSIX permission bits and a non-root user")


@pytest.fixture
def read_only_home(home):
    knowledge.learn("Keep this.", ["role:*"])
    before = _snapshot(home)
    dirs = [home, home / "knowledge"]
    for d in dirs:
        d.chmod(0o500)
    yield before
    for d in dirs:
        d.chmod(0o700)


@posix_perms
def test_read_only_home_fails_writes_clearly_and_still_routes(home, read_only_home, capsys):
    # Writes died with a PermissionError traceback, and route printed nothing because recording the route failed.
    assert cli.main(["learn", "New fact.", "--applies-to", "role:*"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("open-skill: ") and "Permission denied" in err and "Traceback" not in err
    assert cli.main(["route", "add tests", "--project", str(home.parent)]) == 0
    out, err = capsys.readouterr()
    assert json.loads(out)["route_id"] and "not recorded" in err
    assert _snapshot(home) == read_only_home


def _disk_full(*_a, **_k):
    raise OSError(errno.ENOSPC, "No space left on device")


def test_disk_full_while_saving_a_note_keeps_the_old_one(home, monkeypatch):
    nid = knowledge.learn("Keep this.", ["role:*"])
    before = _snapshot(home)
    monkeypatch.setattr(os, "fsync", _disk_full)
    with pytest.raises(OSError):
        knowledge.learn("Keep this.", ["skill:x"])  # rewrites the same note with a wider scope
    assert _snapshot(home) == before and nid


def test_disk_full_during_a_backup_leaves_no_half_written_archive(home, monkeypatch):
    # A partial zip stayed in backups/ under a final name, so `upgrade --rollback` would pick it as the newest.
    import zipfile

    knowledge.learn("One.", ["role:*"])
    knowledge.learn("Two.", ["role:*"])
    real = zipfile.ZipFile.write
    calls = []

    def write(self, *a, **k):
        calls.append(a)
        if len(calls) > 1:
            _disk_full()
        return real(self, *a, **k)

    monkeypatch.setattr(zipfile.ZipFile, "write", write)
    with pytest.raises(OSError):
        userdata.backup(home, "pre-upgrade")
    assert userdata.list_backups(home) == [] and list((home / "backups").iterdir()) == []


def test_disk_full_during_restore_leaves_the_home_as_it_was(home, monkeypatch):
    import zipfile

    knowledge.learn("Old.", ["role:*"])
    archive = userdata.backup(home, "manual")
    knowledge.learn("Newer.", ["role:*"])
    before = {k: v for k, v in _snapshot(home).items() if not k.startswith("backups/")}
    monkeypatch.setattr(zipfile.ZipFile, "extractall", _disk_full)
    with pytest.raises(OSError):
        userdata.restore(home, archive)
    assert {k: v for k, v in _snapshot(home).items() if not k.startswith("backups/")} == before
    assert not [p for p in home.iterdir() if p.name.startswith(".restore")]


needs_symlinks = pytest.mark.skipif(sys.platform == "win32", reason="symlinks need developer mode on Windows")


@needs_symlinks
def test_backup_includes_notes_behind_a_linked_folder(home, tmp_path):
    # rglob does not follow links, so a knowledge/ folder linked to a synced drive was left out of every backup,
    # including the one taken before a migration.
    import zipfile

    elsewhere = tmp_path / "synced notes"
    elsewhere.mkdir()
    home.mkdir()
    (home / "knowledge").symlink_to(elsewhere, target_is_directory=True)
    nid = knowledge.learn("Keep me.", ["role:*"])
    names = zipfile.ZipFile(userdata.backup(home, "manual")).namelist()
    assert f"knowledge/{nid}.md" in names


@needs_symlinks
def test_restore_refuses_to_write_through_a_linked_folder(home, tmp_path, capsys):
    # restore() called shutil.rmtree on the link, which raises, after it had already deleted other entries.
    elsewhere = tmp_path / "synced notes"
    elsewhere.mkdir()
    home.mkdir()
    (home / "knowledge").symlink_to(elsewhere, target_is_directory=True)
    knowledge.learn("Old.", ["role:*"])
    archive = userdata.backup(home, "manual")
    knowledge.learn("Newer.", ["role:*"])
    before = _snapshot(home)
    assert cli.main(["restore", str(archive)]) == 2
    assert "link" in capsys.readouterr().err
    (home / "backups" / archive.name).rename(home / "backups" / archive.name.replace("-manual", "-pre-upgrade"))
    assert cli.main(["upgrade", "--rollback"]) == 2
    assert "link" in capsys.readouterr().err
    before = _snapshot(home)
    assert _snapshot(home) == before and len(list(elsewhere.glob("*.md"))) == 2


@needs_symlinks
def test_a_linked_home_backs_up_and_restores(tmp_path, monkeypatch):
    real = tmp_path / "real home"
    real.mkdir()
    (tmp_path / "link").symlink_to(real, target_is_directory=True)
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "link"))
    knowledge.learn("Old.", ["role:*"])
    archive = userdata.backup(tmp_path / "link", "manual")
    knowledge.learn("Newer.", ["role:*"])
    userdata.restore(tmp_path / "link", archive)
    assert [n["text"] for n in knowledge.load_knowledge()] == ["Old."]
    assert (tmp_path / "link").is_symlink()


def test_a_failure_halfway_through_the_restore_swap_puts_the_old_state_back(home, monkeypatch):
    knowledge.learn("Old.", ["role:*"])
    archive = userdata.backup(home, "manual")
    knowledge.learn("Newer.", ["role:*"])
    (home / "profile.yaml").write_text("roles: {qa-engineer: 1.0}\n", encoding="utf-8")
    before = {k: v for k, v in _snapshot(home).items() if not k.startswith("backups/")}
    real, calls = os.replace, []

    def flaky(src, dst):
        calls.append(src)
        if len(calls) == 6:  # 1 backup rename, 3 entries moved aside, then the second restored entry
            _disk_full()
        return real(src, dst)

    monkeypatch.setattr(os, "replace", flaky)
    with pytest.raises(OSError):
        userdata.restore(home, archive)
    monkeypatch.setattr(os, "replace", real)
    assert {k: v for k, v in _snapshot(home).items() if not k.startswith("backups/")} == before
    assert not [p for p in home.iterdir() if p.name.startswith(".restore")]
