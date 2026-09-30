import datetime as dt
import json
import subprocess
import sys

import pytest

from conftest import git
from open_skill import cli, sessions

T0 = dt.datetime(2026, 9, 30, 8, 0, tzinfo=dt.timezone.utc)


def _record(project, sid):
    return json.loads((project / ".open-skill" / "sessions" / f"{sid}.json").read_text())


# --- record store -------------------------------------------------------------------------------------------------

def test_start_writes_a_record_with_base_and_a_self_ignoring_folder(graph_project):
    s = sessions.start(graph_project, ["pkg/route.py"], "speed up fit", now=T0)
    assert len(s["id"]) == 6 and all(c in "0123456789abcdef" for c in s["id"])
    rec = _record(graph_project, s["id"])
    assert rec == s
    assert set(rec) == {"id", "scope", "task", "started", "seen", "base"}
    assert rec["started"] == rec["seen"] == "2026-09-30T08:00:00Z"
    assert rec["base"] == git(graph_project, "rev-parse", "HEAD").strip()
    assert (graph_project / ".open-skill" / ".gitignore").read_text() == "*\n"


def test_start_without_git_has_no_base(tmp_path):
    assert sessions.start(tmp_path, ["a.py"], "t")["base"] is None


@pytest.mark.parametrize("scope", [[], ["/etc/passwd"], ["../x.py"], ["a/../../x"]])
def test_start_rejects_bad_scopes(tmp_path, scope):
    with pytest.raises(ValueError):
        sessions.start(tmp_path, scope, "t")


@pytest.mark.parametrize("task", ["", "   ", "x" * 201])
def test_start_rejects_bad_tasks(tmp_path, task):
    with pytest.raises(ValueError):
        sessions.start(tmp_path, ["a.py"], task)


def test_task_newlines_become_spaces(tmp_path):
    assert sessions.start(tmp_path, ["a.py"], "two\nlines")["task"] == "two lines"


def test_active_skips_stale_and_unreadable_records(tmp_path):
    fresh = sessions.start(tmp_path, ["a.py"], "fresh", now=T0)
    sessions.start(tmp_path, ["b.py"], "old", now=T0 - dt.timedelta(hours=7))
    folder = tmp_path / ".open-skill" / "sessions"
    (folder / "bad001.json").write_text("{bad")
    (folder / "bad002.json").write_text(json.dumps({"id": "other1"}))  # id differs from the file name
    assert [s["id"] for s in sessions.active(tmp_path, now=T0)] == [fresh["id"]]


def test_touch_refreshes_active_sessions_only(tmp_path):
    s = sessions.start(tmp_path, ["a.py"], "t", now=T0)
    later = T0 + dt.timedelta(hours=1)
    assert sessions.touch(tmp_path, s["id"], now=later)
    assert _record(tmp_path, s["id"])["seen"] == "2026-09-30T09:00:00Z"
    assert not sessions.touch(tmp_path, s["id"], now=later + dt.timedelta(hours=7))  # stale: not revived
    assert _record(tmp_path, s["id"])["seen"] == "2026-09-30T09:00:00Z"
    assert not sessions.touch(tmp_path, "nope00")


def test_end_deletes_even_a_stale_record_and_rejects_unknown_ids(tmp_path):
    s = sessions.start(tmp_path, ["a.py"], "t", now=T0 - dt.timedelta(days=2))
    sessions.end(tmp_path, s["id"])
    assert not (tmp_path / ".open-skill" / "sessions" / f"{s['id']}.json").exists()
    with pytest.raises(KeyError):
        sessions.end(tmp_path, s["id"])


def test_prune_removes_stale_and_unreadable_records(tmp_path):
    keep = sessions.start(tmp_path, ["a.py"], "keep", now=T0)
    sessions.start(tmp_path, ["b.py"], "old", now=T0 - dt.timedelta(hours=7))
    (tmp_path / ".open-skill" / "sessions" / "bad001.json").write_text("{bad")
    assert sessions.prune(tmp_path, now=T0) == 2
    left = sorted(p.name for p in (tmp_path / ".open-skill" / "sessions").glob("*.json"))
    assert left == [f"{keep['id']}.json"]


WRITER = """
import sys
from pathlib import Path
from open_skill import sessions
sessions.start(Path(sys.argv[1]), ["a.py"], "writer " + sys.argv[2])
"""


def test_sessions_started_at_once_are_all_recorded(tmp_path):
    procs = [subprocess.Popen([sys.executable, "-c", WRITER, str(tmp_path), str(i)]) for i in range(8)]
    assert all(p.wait(timeout=120) == 0 for p in procs)
    assert len(sessions.active(tmp_path)) == 8
