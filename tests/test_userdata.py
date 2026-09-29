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


def test_migrate_runs_steps_in_order_with_backup(tmp_path, monkeypatch):
    home = _layer(tmp_path / "h")
    calls = []
    monkeypatch.setattr(userdata, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(userdata, "MIGRATIONS", {
        0: ("first", lambda h, dry: calls.append((0, dry)) or ["did 0"]),
        1: ("second", lambda h, dry: calls.append((1, dry)) or ["did 1"]),
    })
    actions = userdata.migrate(home)
    assert calls == [(0, False), (1, False)]
    assert actions[0].startswith("backed up to") and "v1 -> v2: second" in actions
    assert userdata.data_version(home) == 2
    assert userdata.migrate(home) == []


def test_migrate_dry_run_changes_nothing(tmp_path, monkeypatch):
    home = _layer(tmp_path / "h")
    monkeypatch.setattr(userdata, "MIGRATIONS", {0: ("first", lambda h, dry: ["would do"] if dry else ["did"])})
    actions = userdata.migrate(home, dry_run=True)
    assert "  would do" in actions
    assert userdata.data_version(home) == 0 and userdata.list_backups(home) == []


def test_v0_to_v1_keeps_bodies_byte_for_byte(tmp_path):
    import yaml
    from open_skill import frontmatter
    home = tmp_path / "h"
    k = home / "knowledge"
    k.mkdir(parents=True)
    seed_body = "Use MERGE on the business key.\n\n  Keep   spacing  exactly.\n"
    user_body = "My own note, edited by hand.\n"
    (k / "k-seed.md").write_text("---\nid: k-seed\ntype: pitfall\nsource: seed\napplies_to: [role:data-engineer]\n---\n" + seed_body)
    (k / "k-user.md").write_text("---\nid: k-user\ntype: lesson\nsource: user\napplies_to: ['role:*']\n---\n" + user_body)
    (k / "broken.md").write_text("no frontmatter at all")
    actions = userdata.migrate(home)
    assert userdata.data_version(home) == 1
    seed_meta, _ = frontmatter.parse((k / "k-seed.md").read_text())
    assert seed_meta["schema"] == 1 and seed_meta["seed_hash"] == userdata.text_hash(seed_body)
    assert (k / "k-seed.md").read_text().endswith(seed_body)
    assert (k / "k-user.md").read_text().endswith(user_body)
    assert "seed_hash" not in frontmatter.parse((k / "k-user.md").read_text())[0]
    assert (k / "broken.md").read_text() == "no frontmatter at all"
    assert any(a.startswith("backed up to") for a in actions)
    assert userdata.migrate(home) == []
