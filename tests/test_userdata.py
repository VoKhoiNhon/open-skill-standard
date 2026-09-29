from pathlib import Path

import pytest

from open_skill import userdata


def test_atomic_write_creates_parents_and_replaces(tmp_path):
    p = tmp_path / "a" / "b.txt"
    userdata.atomic_write(p, "one")
    userdata.atomic_write(p, "two")
    assert p.read_text() == "two"
    assert [x.name for x in p.parent.iterdir()] == ["b.txt"]  # no temp files left behind


def test_atomic_write_keeps_old_content_on_failure(tmp_path, monkeypatch):
    p = tmp_path / "b.txt"
    userdata.atomic_write(p, "safe")

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(userdata.os, "replace", boom)
    with pytest.raises(OSError):
        userdata.atomic_write(p, "partial")
    assert p.read_text() == "safe"
    assert [x.name for x in tmp_path.iterdir()] == ["b.txt"]


def test_fresh_home_is_current(tmp_path):
    assert userdata.data_version(tmp_path / "new") == userdata.SCHEMA_VERSION


def test_unversioned_existing_layout_is_version_zero(tmp_path):
    (tmp_path / "knowledge").mkdir()
    assert userdata.data_version(tmp_path) == 0


def test_version_file_round_trip(tmp_path):
    userdata.write_version(tmp_path, 7)
    assert userdata.data_version(tmp_path) == 7


def test_ensure_writable_stamps_fresh_home(tmp_path):
    userdata.ensure_writable(tmp_path / "h")
    assert (tmp_path / "h" / "VERSION").read_text().strip() == str(userdata.SCHEMA_VERSION)


def test_newer_data_blocks_writes(tmp_path):
    userdata.write_version(tmp_path, userdata.SCHEMA_VERSION + 1)
    with pytest.raises(userdata.NewerDataError):
        userdata.ensure_writable(tmp_path)


def _layer(home):
    (home / "knowledge").mkdir(parents=True)
    (home / "knowledge" / "k-a.md").write_text("---\nid: k-a\n---\nA")
    (home / "profile.yaml").write_text("roles: {qa-engineer: 1.0}\n")
    return home


def test_backup_zips_layer_but_not_other_backups(tmp_path):
    import zipfile
    home = _layer(tmp_path / "h")
    first = userdata.backup(home)
    second = userdata.backup(home, "again")
    names = zipfile.ZipFile(second).namelist()
    assert sorted(names) == ["knowledge/k-a.md", "profile.yaml"]
    assert first != second and first.exists()


def test_backup_of_empty_home_is_none(tmp_path):
    assert userdata.backup(tmp_path / "empty") is None



def test_backup_names_sort_in_creation_order(tmp_path):
    home = _layer(tmp_path / "h")
    made = [userdata.backup(home, "auto") for _ in range(5)]
    assert sorted(made) == made and len(set(made)) == 5


def test_prune_keeps_newest_of_one_label_only(tmp_path):
    home = _layer(tmp_path / "h")
    autos = [userdata.backup(home, "auto") for _ in range(4)]
    manual = userdata.backup(home, "manual")
    removed = userdata.prune_backups(home, "auto", keep=2)
    assert removed == autos[:2]
    assert set(userdata.list_backups(home)) == {autos[2], autos[3], manual}


def test_restore_round_trip_with_safety_backup(tmp_path):
    home = _layer(tmp_path / "h")
    snap = userdata.backup(home)
    (home / "knowledge" / "k-a.md").write_text("changed")
    (home / "knowledge" / "k-new.md").write_text("new")
    safety = userdata.restore(home, snap)
    assert (home / "knowledge" / "k-a.md").read_text().endswith("A")
    assert not (home / "knowledge" / "k-new.md").exists()
    assert safety.exists() and safety in userdata.list_backups(home) and snap.exists()


def test_restore_rejects_path_traversal(tmp_path):
    import zipfile
    home = _layer(tmp_path / "h")
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../outside.txt", "x")
    with pytest.raises(userdata.UnsafeBackupError):
        userdata.restore(home, evil)
    assert not (tmp_path / "outside.txt").exists()
    assert (home / "profile.yaml").exists()
