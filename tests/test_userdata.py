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
