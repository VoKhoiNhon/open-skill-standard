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
