import datetime as dt
import json
import os
import shutil

import pytest

from conftest import GRAPHIFY_FIXTURE, git
from open_skill import cli, sessions


def _graph():
    return json.loads(GRAPHIFY_FIXTURE.read_text(encoding="utf-8"))


def _run(capsys, *argv):
    code = cli.main(["session", *argv])
    out, err = capsys.readouterr()
    return code, out, err


# --- the walk (T006) ----------------------------------------------------------------------------------------------

def test_walk_reaches_callers_and_package_importers_within_two_hops(graph_project):
    got = sessions.affected_files(graph_project, _graph(), ["pkg/route.py"])
    assert set(got) == {"pkg/cli.py", "pkg/deep.py", "tests/test_route.py", "tests/test_cli.py"}


def test_walk_needs_package_import_resolution_to_find_the_test(graph_project):
    # The fixture has Graphify's real shape: `from pkg import (route,)` points at pkg/__init__.py, not route.py.
    got = sessions.affected_files(graph_project, _graph(), ["pkg/route.py"], resolve_packages=False)
    assert "tests/test_route.py" not in got and "tests/test_cli.py" not in got


def test_walk_stops_at_two_hops_and_skips_changed_contains_and_external_nodes(graph_project):
    got = sessions.affected_files(graph_project, _graph(), ["pkg/route.py"])
    assert "pkg/far.py" not in got and "pkg/route.py" not in got and "" not in got
    got = sessions.affected_files(graph_project, _graph(), ["pkg/deep.py"])
    assert got == ["pkg/far.py"]  # contains links are not followed: nothing else reaches deep.py


def test_walk_follows_only_the_listed_relations(graph_project):
    g = _graph()
    for link in g["links"]:
        if link["relation"] == "calls":
            link["relation"] = "rationale_for"
    assert sessions.affected_files(graph_project, g, ["pkg/route.py"]) == ["tests/test_route.py"]


def test_walk_never_reads_files_outside_the_project(graph_project, tmp_path):
    secret = tmp_path / "outside.py"
    secret.write_text("from pkg import route\n", encoding="utf-8")
    g = _graph()
    g["links"].append({"source": "tests_test_cli", "target": "pkg_init", "relation": "imports_from",
                       "source_file": str(secret), "source_location": "L1"})
    g["links"].append({"source": "tests_test_cli", "target": "pkg_init", "relation": "imports_from",
                       "source_file": "../outside.py", "source_location": "L1"})
    assert set(sessions.affected_files(graph_project, g, ["pkg/route.py"])) == {
        "pkg/cli.py", "pkg/deep.py", "tests/test_route.py", "tests/test_cli.py"}


# --- changed files (T007) -----------------------------------------------------------------------------------------

def test_changed_files_are_tracked_edits_plus_untracked_files(graph_project):
    (graph_project / "pkg" / "route.py").write_text("changed\n", encoding="utf-8")
    (graph_project / "new.py").write_text("x\n", encoding="utf-8")
    files, warnings = sessions.changed_files(graph_project)
    assert files == ["new.py", "pkg/route.py"] and warnings == []


def test_changed_files_keep_non_ascii_names_as_they_are(graph_project):
    # git quotes such paths ("pkg/t\303\263m...") unless asked not to, and they then match no scope
    (graph_project / "pkg" / "tóm tắt.py").write_text("x\n", encoding="utf-8")
    git(graph_project, "add", "-A")
    git(graph_project, "commit", "-qm", "add")
    (graph_project / "pkg" / "tóm tắt.py").write_text("y\n", encoding="utf-8")
    (graph_project / "ghi chú.md").write_text("x\n", encoding="utf-8")
    assert sessions.changed_files(graph_project)[0] == ["ghi chú.md", "pkg/tóm tắt.py"]


def test_changed_files_since_base_include_committed_work(graph_project):
    base = git(graph_project, "rev-parse", "HEAD").strip()
    (graph_project / "pkg" / "route.py").write_text("changed\n", encoding="utf-8")
    git(graph_project, "commit", "-qam", "work")
    assert sessions.changed_files(graph_project)[0] == []
    assert sessions.changed_files(graph_project, base)[0] == ["pkg/route.py"]


def test_changed_files_fall_back_to_head_when_base_is_gone(graph_project):
    (graph_project / "pkg" / "route.py").write_text("changed\n", encoding="utf-8")
    files, warnings = sessions.changed_files(graph_project, "0" * 40)
    assert files == ["pkg/route.py"]
    assert warnings == [f"session base {'0' * 40} is gone; compared with HEAD"]


def test_changed_files_ignore_our_own_bookkeeping(graph_project):
    sessions.start(graph_project, ["pkg/**"], "t")
    (graph_project / "graphify-out" / "graph.json").write_text("{}", encoding="utf-8")
    assert sessions.changed_files(graph_project)[0] == []


def test_changed_files_without_git_or_commits(tmp_path):
    assert sessions.changed_files(tmp_path) is None
    git(tmp_path, "init", "-q")
    assert sessions.changed_files(tmp_path) is None


# --- the command (T008) -------------------------------------------------------------------------------------------

@pytest.fixture
def two_sessions(graph_project):
    a = sessions.start(graph_project, ["pkg/route.py"], "speed up fit")
    b = sessions.start(graph_project, ["tests/**"], "add fixtures for route tests")
    return a["id"], b["id"]


def test_update_warns_about_a_file_in_another_sessions_scope(graph_project, fake_graphify, two_sessions, capsys):
    a, b = two_sessions
    (graph_project / "pkg" / "route.py").write_text("def fit():\n    return 3\n", encoding="utf-8")
    code, out, err = _run(capsys, "update", "--session", a, "--project", str(graph_project))
    assert code == 0
    assert "changed: pkg/route.py" in out
    assert f'⚠ tests/test_route.py is in session {b} ("add fixtures for route tests"), reached from pkg/route.py' in out
    assert f"⚠ tests/test_cli.py is in session {b}" in out


def test_update_json_shape(graph_project, fake_graphify, two_sessions, capsys):
    a, b = two_sessions
    (graph_project / "pkg" / "route.py").write_text("x\n", encoding="utf-8")
    code, out, _ = _run(capsys, "update", "--session", a, "--project", str(graph_project), "--json")
    r = json.loads(out)
    assert code == 0
    assert set(r) == {"session", "graph", "base", "changed", "git", "affected", "conflicts", "others", "warnings"}
    assert r["session"] == a and r["git"] is True and r["changed"] == ["pkg/route.py"]
    assert r["graph"] == {"refreshed": True, "nodes": 13, "edges": 11}
    assert "tests/test_route.py" in r["affected"]
    assert {"file": "tests/test_route.py", "session": b, "task": "add fixtures for route tests",
            "via": "pkg/route.py"} in r["conflicts"]
    assert r["base"] == sessions.get(graph_project, a)["base"]


def test_update_after_committing_still_sees_the_change(graph_project, fake_graphify, two_sessions, capsys):
    a, b = two_sessions
    (graph_project / "pkg" / "route.py").write_text("x\n", encoding="utf-8")
    git(graph_project, "commit", "-qam", "work")
    _, out, _ = _run(capsys, "update", "--session", a, "--project", str(graph_project), "--json")
    r = json.loads(out)
    assert r["changed"] == ["pkg/route.py"]
    assert any(c["session"] == b and c["file"] == "tests/test_route.py" for c in r["conflicts"])


def test_another_sessions_own_change_is_its_work_not_a_conflict(graph_project, fake_graphify, two_sessions, capsys):
    a, b = two_sessions
    (graph_project / "tests" / "test_cli.py").write_text("x\n", encoding="utf-8")  # inside B's scope only: B's work (N1, option b)
    code, out, _ = _run(capsys, "update", "--session", a, "--project", str(graph_project), "--json")
    r = json.loads(out)
    assert code == 0 and r["conflicts"] == [] and r["changed"] == ["tests/test_cli.py"]
    assert r["others"] == [{"file": "tests/test_cli.py", "session": b, "task": "add fixtures for route tests"}]
    assert r["affected"] == []  # another session's change is not walked for this session


def test_others_are_listed_in_text_output(graph_project, fake_graphify, two_sessions, capsys):
    a, b = two_sessions
    (graph_project / "tests" / "test_cli.py").write_text("x\n", encoding="utf-8")
    _, out, _ = _run(capsys, "update", "--session", a, "--project", str(graph_project))
    assert f'· tests/test_cli.py changed in session {b} ("add fixtures for route tests"); counted as its work' in out
    assert "⚠" not in out


def test_own_edit_inside_another_scope_is_still_a_conflict(graph_project, fake_graphify, capsys):
    a = sessions.start(graph_project, ["pkg/**", "tests/test_cli.py"], "mine")["id"]
    b = sessions.start(graph_project, ["tests/**"], "theirs")["id"]
    (graph_project / "tests" / "test_cli.py").write_text("x\n", encoding="utf-8")  # in both scopes: A may edit it, B must hear
    r = json.loads(_run(capsys, "update", "--session", a, "--project", str(graph_project), "--json")[1])
    assert r["others"] == []
    assert {"file": "tests/test_cli.py", "session": b, "task": "theirs", "via": "tests/test_cli.py"} in r["conflicts"]


def test_without_a_session_every_changed_file_in_a_scope_is_a_conflict(graph_project, fake_graphify, two_sessions,
                                                                       capsys):
    _, b = two_sessions
    (graph_project / "tests" / "test_cli.py").write_text("x\n", encoding="utf-8")
    r = json.loads(_run(capsys, "update", "--project", str(graph_project), "--json")[1])
    assert r["others"] == []
    assert {"file": "tests/test_cli.py", "session": b, "task": "add fixtures for route tests",
            "via": "tests/test_cli.py"} in r["conflicts"]


def test_update_without_conflicts(graph_project, fake_graphify, capsys):
    a = sessions.start(graph_project, ["pkg/**"], "all of pkg")["id"]
    (graph_project / "pkg" / "route.py").write_text("x\n", encoding="utf-8")
    code, out, _ = _run(capsys, "update", "--session", a, "--project", str(graph_project))
    assert code == 0 and "⚠" not in out and "affected: 4 files" in out and "no conflicts" in out


def _age(project, sid, hours):
    rec = sessions.get(project, sid)
    rec["seen"] = sessions._stamp(sessions._now() - dt.timedelta(hours=hours))
    (project / ".open-skill" / "sessions" / f"{sid}.json").write_text(json.dumps(rec), encoding="utf-8")
    return rec["seen"]


def test_update_refreshes_the_named_session(graph_project, fake_graphify, two_sessions, capsys):
    a, _ = two_sessions
    before = _age(graph_project, a, 1)
    assert _run(capsys, "update", "--session", a, "--project", str(graph_project))[0] == 0
    assert sessions.get(graph_project, a)["seen"] > before


def test_update_warns_on_a_stale_or_unknown_session_and_does_not_revive_it(graph_project, fake_graphify,
                                                                              two_sessions, capsys):
    a, _ = two_sessions
    before = _age(graph_project, a, 7)
    code, _, err = _run(capsys, "update", "--session", a, "--project", str(graph_project))
    assert code == 0
    assert f"session {a} is unknown or stale; checked against all active sessions" in err
    assert sessions.get(graph_project, a)["seen"] == before
    code, _, err = _run(capsys, "update", "--session", "ffffff", "--project", str(graph_project))
    assert code == 0 and "session ffffff is unknown or stale" in err


def test_update_without_graphify(graph_project, monkeypatch, capsys):
    monkeypatch.setenv("PATH", "/nonexistent")
    code, _, err = _run(capsys, "update", "--project", str(graph_project))
    assert code == 2 and "uv tool install graphifyy" in err


def test_update_without_a_graph_never_builds_one(graph_project, fake_graphify, capsys):
    log = fake_graphify()
    shutil.rmtree(graph_project / "graphify-out")
    code, _, err = _run(capsys, "update", "--project", str(graph_project))
    assert code == 2 and "graphify extract . --code-only" in err
    assert not log.exists()


def test_update_passes_a_failed_refresh_through_and_never_forces(graph_project, fake_graphify, capsys):
    log = fake_graphify(exit_code=1, stderr="Nothing to update or rebuild failed")
    code, _, err = _run(capsys, "update", "--project", str(graph_project))
    assert code == 1
    assert "Nothing to update or rebuild failed" in err and "graphify update . --force" in err
    assert "--force" not in log.read_text(encoding="utf-8")


def test_update_outside_git_skips_the_conflict_check(graph_project, fake_graphify, capsys):
    for f in (graph_project / ".git").rglob("*"):
        f.chmod(0o700)  # git's object files are read-only, and Windows refuses to delete read-only files
    shutil.rmtree(graph_project / ".git")
    code, out, err = _run(capsys, "update", "--project", str(graph_project), "--json")
    assert code == 0 and "conflict check skipped" in err
    assert json.loads(out)["git"] is False


def test_update_calls_graphify_update_in_the_project_root(graph_project, fake_graphify, capsys):
    log = fake_graphify()
    _run(capsys, "update", "--project", str(graph_project))
    assert log.read_text(encoding="utf-8").splitlines() == [f"{os.path.realpath(graph_project)} update ."]
