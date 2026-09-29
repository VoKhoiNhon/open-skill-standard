import json
import shutil
from pathlib import Path

import pytest
import yaml

from open_skill import cli

FIX = Path(__file__).parent / "fixtures"
REPO = Path(__file__).parents[1]


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))
    monkeypatch.setenv("HOME", str(FIX / "home"))


def run(capsys, *argv):
    code = cli.main(["--registry", str(FIX / "repo"), *argv])
    return code, capsys.readouterr().out


def test_route_json_and_explain(capsys, tmp_path):
    (tmp_path / "p").mkdir()
    code, out = run(capsys, "route", "add an export endpoint", "--project", str(tmp_path / "p"), "--role", "data-engineer")
    assert code == 0
    r = json.loads(out)
    assert r["chain"] and r["route_id"].startswith("r-")
    code, out = run(capsys, "route", "add an export endpoint", "--project", str(tmp_path / "p"), "--explain")
    assert "score=" in out and out.startswith("route r-")


def test_feedback_appends_event(capsys, tmp_path):
    code, _ = run(capsys, "feedback", "r-1", "--ran", "a,b", "--outcome", "ok")
    assert code == 0
    line = (tmp_path / "h" / "events.jsonl").read_text().strip()
    assert json.loads(line)["ran"] == ["a", "b"]


def test_build_then_check(capsys, tmp_path):
    root = tmp_path / "root"
    shutil.copytree(FIX / "repo", root)
    shutil.copytree(REPO / "spec", root / "spec", dirs_exist_ok=True)
    assert cli.main(["--registry", str(root), "build", "--root", str(root)]) == 0
    assert (root / "skills/open-skill-router/references/roles/data-engineer.md").exists()
    assert (root / "dist/index.db").exists()
    assert cli.main(["--registry", str(root), "build", "--root", str(root), "--check"]) == 0
    (root / "dist/graph.mmd").write_text("tampered")
    assert cli.main(["--registry", str(root), "build", "--root", str(root), "--check"]) == 1


def test_adapter_draft_and_check(capsys):
    code, out = run(capsys, "adapter", "draft", "--source", "superpowers", "--from", str(FIX / "upstream"))
    doc = yaml.safe_load(out)
    assert {s["name"] for s in doc["skills"]} == {"test-driven-development", "new-one"}
    assert next(s for s in doc["skills"] if s["name"] == "new-one")["phases"] == ["review"]
    code, out = run(capsys, "adapter", "check", "--source", "superpowers", "--from", str(FIX / "upstream"))
    assert code == 1 and "+ new-one" in out and "- brainstorming" in out


def test_init_learn_forget(capsys, tmp_path):
    assert run(capsys, "init", "--role", "data-engineer=1")[0] == 0
    code, out = run(capsys, "learn", "Check nulls on keys", "--applies-to", "role:data-engineer")
    nid = out.strip()
    assert code == 0 and nid.startswith("k-")
    assert run(capsys, "forget", nid)[0] == 0
    assert run(capsys, "learn", "password=abc", "--applies-to", "role:x")[0] == 2
    assert run(capsys, "init", "--role", "astronaut")[0] == 2


def test_validate_scan_doctor_graph(capsys):
    assert run(capsys, "validate")[0] == 0
    code, out = run(capsys, "scan")
    assert "superpowers:test-driven-development" in out
    code, out = run(capsys, "doctor")
    assert "superpowers" in out and "no profile yet" in out
    code, out = run(capsys, "graph")
    assert out.startswith("graph LR")
