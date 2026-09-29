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


def test_newer_user_data_gives_clear_error(capsys, tmp_path):
    from open_skill import userdata
    userdata.write_version(tmp_path / "h", userdata.SCHEMA_VERSION + 1)
    code = cli.main(["--registry", str(FIX / "repo"), "learn", "x", "--applies-to", "role:*"])
    assert code == 3
    assert "Upgrade open-skill" in capsys.readouterr().err


def test_backup_command_and_list(capsys, tmp_path):
    run(capsys, "learn", "Keep backfills bounded", "--applies-to", "role:data-engineer")
    code, out = run(capsys, "backup")
    made = Path(out.strip())
    assert code == 0 and made.exists() and made.parent.name == "backups"
    code, out = run(capsys, "backup", "--list")
    assert str(made) in out


def test_restore_command(capsys, tmp_path):
    run(capsys, "learn", "First note", "--applies-to", "role:*")
    snap = run(capsys, "backup")[1].strip()
    run(capsys, "learn", "Second note", "--applies-to", "role:*")
    code, out = run(capsys, "restore", snap)
    assert code == 0 and "previous state saved" in out
    texts = [p.read_text() for p in (tmp_path / "h" / "knowledge").glob("*.md")]
    assert any("First note" in t for t in texts) and not any("Second note" in t for t in texts)


def test_migrate_command_dry_run_then_apply(capsys, tmp_path):
    k = tmp_path / "h" / "knowledge"
    k.mkdir(parents=True)
    (k / "k-a.md").write_text("---\nid: k-a\ntype: lesson\nsource: user\napplies_to: ['role:*']\n---\nText\n")
    code, out = run(capsys, "migrate", "--dry-run")
    assert code == 0 and "dry run" in out and "would update k-a.md" in out
    assert not (tmp_path / "h" / "VERSION").exists()
    code, out = run(capsys, "migrate")
    assert "updated k-a.md" in out and (tmp_path / "h" / "VERSION").exists()
    assert "up to date" in run(capsys, "migrate")[1]


def test_playbook_renders_seed_objects_as_text():
    from open_skill import generate, registry
    reg = registry.load(FIX / "repo")
    reg.roles["data-engineer"]["seeds"] = [{"id": "merge-key", "text": "Use MERGE on the key."}, "Legacy seed."]
    text = generate.role_playbook(reg, "data-engineer")
    assert "- Use MERGE on the key." in text and "- Legacy seed." in text and "merge-key" not in text


def test_init_with_the_real_registry_seeds(capsys, tmp_path):
    code = cli.main(["init", "--role", "data-engineer"])
    assert code == 0
    assert list((tmp_path / "h" / "knowledge").glob("*.md"))


def test_seeds_sync_command(capsys, tmp_path):
    assert run(capsys, "seeds", "sync")[0] == 1  # no profile yet
    run(capsys, "init", "--role", "data-engineer")
    code, out = run(capsys, "seeds", "sync", "--dry-run")
    assert code == 0 and "up to date" in out

