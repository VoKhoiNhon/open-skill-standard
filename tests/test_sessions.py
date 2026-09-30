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


# --- the command (T013) -------------------------------------------------------------------------------------------

def _cli(capsys, *argv):
    code = cli.main(["session", *argv])
    out, err = capsys.readouterr()
    return code, out, err


def test_cli_start_prints_the_id_and_json_prints_the_record(graph_project, capsys):
    code, out, _ = _cli(capsys, "start", "--scope", "pkg/**", "--task", "speed up fit", "--project", str(graph_project))
    sid = out.splitlines()[0]
    assert code == 0 and sessions.get(graph_project, sid)["task"] == "speed up fit"
    code, out, _ = _cli(capsys, "start", "--scope", "tests/**", "--task", "t", "--project", str(graph_project), "--json")
    assert code == 0 and json.loads(out)["scope"] == ["tests/**"]


def test_cli_start_warns_on_overlap_and_on_globs_matching_nothing(graph_project, capsys):
    _, out, _ = _cli(capsys, "start", "--scope", "pkg/**", "--task", "speed up fit", "--project", str(graph_project))
    first = out.splitlines()[0]
    code, out, err = _cli(capsys, "start", "--scope", "pkg/route.py", "--scope", "docs/new/**", "--task", "t2",
                          "--project", str(graph_project))
    assert code == 0 and out.strip()
    assert f'warning: scope overlaps session {first} ("speed up fit"): pkg/route.py' in err
    assert "warning: scope glob matches no file: docs/new/**" in err


@pytest.mark.parametrize("argv", [["--task", "t"], ["--scope", "/abs", "--task", "t"],
                                  ["--scope", "../up", "--task", "t"], ["--scope", "a.py", "--task", ""]])
def test_cli_start_rejects_bad_input(graph_project, capsys, argv):
    try:
        code = _cli(capsys, "start", *argv, "--project", str(graph_project))[0]
    except SystemExit as e:  # argparse: a required flag is missing
        code = e.code
    assert code == 2 and not sessions.active(graph_project)


def test_cli_list_is_newest_first_and_never_touches_seen(graph_project, capsys):
    old = sessions.start(graph_project, ["pkg/**"], "older", now=sessions._now() - dt.timedelta(hours=2))
    new = sessions.start(graph_project, ["tests/**"], "newer")
    sessions.start(graph_project, ["x.py"], "stale", now=sessions._now() - dt.timedelta(hours=7))
    code, out, _ = _cli(capsys, "list", "--project", str(graph_project))
    lines = out.splitlines()
    assert code == 0 and len(lines) == 2
    assert lines[0].startswith(new["id"]) and lines[1].startswith(old["id"]) and "older" in lines[1]
    assert "seen 120m ago" in lines[1] and "pkg/**" in lines[1]
    _, out, _ = _cli(capsys, "list", "--project", str(graph_project), "--json")
    assert [s["id"] for s in json.loads(out)] == [new["id"], old["id"]]
    assert sessions.get(graph_project, old["id"])["seen"] == old["seen"]


def test_cli_list_prune(graph_project, capsys):
    sessions.start(graph_project, ["x.py"], "stale", now=sessions._now() - dt.timedelta(hours=7))
    (graph_project / ".open-skill" / "sessions" / "bad001.json").write_text("{bad")
    code, out, err = _cli(capsys, "list", "--prune", "--project", str(graph_project))
    assert code == 0 and "pruned 2 record(s)" in err and out == ""


def test_cli_end(graph_project, capsys):
    s = sessions.start(graph_project, ["x.py"], "t")
    assert _cli(capsys, "end", s["id"], "--project", str(graph_project))[0] == 0
    code, _, err = _cli(capsys, "end", s["id"], "--project", str(graph_project))
    assert code == 2 and f"open-skill: no such session: {s['id']}" in err
