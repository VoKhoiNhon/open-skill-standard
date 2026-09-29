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


def test_route_why_not(capsys, tmp_path):
    (tmp_path / "p").mkdir()
    base = ("route", "add an export endpoint", "--project", str(tmp_path / "p"), "--role", "data-engineer")
    code, out = run(capsys, *base, "--why-not", "spec-kit/plan")
    assert code == 0 and "spec-kit/plan is not in the chain" in out and "not installed → specify init" in out
    code, out = run(capsys, *base, "--why-not", "superpowers:test-driven-development")
    assert code == 0 and "is in the chain" in out
    assert run(capsys, *base, "--why-not", "nobody/nothing")[0] == 2
    assert not (tmp_path / "h" / "events.jsonl").exists()


def test_search_filters_by_role_phase_and_source(capsys):
    code, out = run(capsys, "search", "plan spec test data", "--phase", "plan")
    assert code == 0
    assert {line.split()[1] for line in out.splitlines()} == {"spec-kit/plan", "superpowers/writing-plans", "superpowers/brainstorming"}
    code, out = run(capsys, "search", "plan spec test data", "--phase", "plan", "--source", "spec-kit")
    assert [line.split()[1] for line in out.splitlines()] == ["spec-kit/plan"]
    code, out = run(capsys, "search", "plan spec test data", "--role", "data-analyst")
    assert [line.split()[1] for line in out.splitlines()] == ["knowledge-work-data/validate-data"]
    code, out = run(capsys, "search", "plan", "--limit", "1", "--phase", "plan")
    assert len(out.splitlines()) == 1
    for bad in (("--role", "astronaut"), ("--phase", "dreaming"), ("--source", "nowhere")):
        assert run(capsys, "search", "plan", *bad)[0] == 2


def test_search_installed_only(capsys):
    code, out = run(capsys, "search", "plan spec test data", "--installed")
    assert code == 0
    assert [line.split()[1] for line in out.splitlines()] == ["superpowers/test-driven-development"]
    code, out = run(capsys, "search", "lint", "--installed", "--source", "harvested")
    assert [line.split()[1] for line in out.splitlines()] == ["harvested/lint-helper"]


def test_search_without_query_lists_filtered_skills(capsys):
    code, out = run(capsys, "search", "--source", "spec-kit")
    assert code == 0
    assert [line.split()[1] for line in out.splitlines()] == ["spec-kit/implement", "spec-kit/plan", "spec-kit/specify"]
    assert all(line.split()[0] == "-" for line in out.splitlines())
    assert run(capsys, "search")[0] == 2


def test_route_explain_shows_why_this_window(capsys, tmp_path):
    (tmp_path / "p").mkdir()
    base = ("route", "--project", str(tmp_path / "p"), "--role", "data-engineer", "--explain")
    code, out = run(capsys, "route", "add an export endpoint", *base[1:])
    assert "target build from phase keywords: add, endpoint" in out
    assert "size medium: no size keywords, the default" in out
    assert "phase window: plan → build → verify → review (medium build task: starts at plan" in out
    code, out = run(capsys, "route", "the orders thing", *base[1:], "--size", "small")
    assert "phase: build (guessed, no signal); pass --phase if you know it" in out and "size small: given" in out
    assert "target=build (guessed)" in out
    code, out = run(capsys, "route", "fix a typo", *base[1:])
    assert "size small from size keywords: typo" in out


def test_route_explain_lists_runner_ups_with_scores(capsys, tmp_path, monkeypatch):
    from open_skill import registry, route as route_mod, scan
    reg = registry.load(FIX / "repo")
    everything = [scan.Installed(sid, sid, "/x", s.get("description", ""), False) for sid, s in reg.skills.items()]
    monkeypatch.setattr(scan, "scan", lambda *a, **k: everything)
    (tmp_path / "p").mkdir()
    r = route_mod.route("add an export endpoint", tmp_path / "p", reg, everything, role="fullstack-developer",
                        record=False, decisions=True)
    plan = next(s for s in r["chain"] if s["phase"] == "plan")
    losers = sorted((d for d in r["decisions"]["candidates"] if d["phase"] == "plan" and d["outcome"] == "lower-score"),
                    key=lambda d: -d["score"])
    code, out = run(capsys, "route", "add an export endpoint", "--project", str(tmp_path / "p"),
                    "--role", "fullstack-developer", "--explain", "--no-record")
    step = out.split(f"[plan] {plan['invoke']}")[1].splitlines()
    close = lambda d: " (close call)" if d["id"] == plan.get("runner_up") else ""  # noqa: E731
    assert step[1].strip() == "runner-ups: " + ", ".join(f"{d['id']} {d['score']}{close(d)}" for d in losers[:3])


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
    assert "agents: claude-code (" in out and "codex (" in out and "demo-agent" not in out
    assert "open-skill install open-skill-router --agent codex" in out
    code, out = run(capsys, "graph")
    assert out.startswith("graph LR")


def test_graph_html_writes_one_file(capsys, tmp_path):
    dest = tmp_path / "graph.html"
    code, out = run(capsys, "graph", "--format", "html", "--out", str(dest))
    assert code == 0 and str(dest) in out
    html = dest.read_text()
    assert html.startswith("<!doctype html>") and "superpowers/writing-plans" in html
    code, out = run(capsys, "graph", "--format", "json", "--out", str(tmp_path / "g.json"))
    assert json.loads((tmp_path / "g.json").read_text())["nodes"]


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


def test_seeds_review_commands(capsys, tmp_path):
    from open_skill import knowledge
    knowledge.sync_seeds(["data-engineer"], {"data-engineer": [{"id": "n", "text": "Old."}]})
    p = next((tmp_path / "h" / "knowledge").glob("*.md"))
    p.write_text(p.read_text().replace("Old.", "Mine."))
    knowledge.sync_seeds(["data-engineer"], {"data-engineer": [{"id": "n", "text": "New."}]})
    code, out = run(capsys, "seeds", "diff")
    assert code == 0 and "-Mine." in out and "+New." in out
    code, out = run(capsys, "seeds", "keep", "data-engineer/n")
    assert "kept your version" in out
    assert "no seed updates waiting" in run(capsys, "seeds", "accept")[1]


def test_upgrade_command_and_rollback(capsys, tmp_path):
    run(capsys, "init", "--role", "data-engineer")
    code, out = run(capsys, "upgrade", "--dry-run")
    assert code == 0 and "dry run" in out
    code, out = run(capsys, "upgrade")
    assert code == 0 and "backed up to" in out
    code, out = run(capsys, "upgrade", "--rollback")
    assert code == 0 and out.startswith("restored")


def test_status_reports_versions_and_pending_work(capsys, tmp_path):
    (tmp_path / "h" / "knowledge").mkdir(parents=True)
    code, out = run(capsys, "status")
    assert code == 0 and "data_schema              0" in out and "open-skill upgrade" in out
    code, out = run(capsys, "status", "--json")
    info = json.loads(out)
    assert info["pending_migrations"] == 1 and info["cli_schema"] >= 1


def test_doctor_points_to_upgrade_and_reviews(capsys, tmp_path):
    (tmp_path / "h" / "knowledge").mkdir(parents=True)
    code, out = run(capsys, "doctor")
    assert "open-skill upgrade" in out


def test_lint_exit_codes_and_json(capsys, tmp_path):
    d = tmp_path / "s" / "warn-only"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: warn-only\ndescription: Does a thing.\nextra: x\n---\nbody\n")
    code, out = run(capsys, "lint", str(tmp_path / "s"))
    assert code == 0 and "0 error(s), 1 warning(s)" in out
    assert run(capsys, "lint", "--strict", str(tmp_path / "s"))[0] == 1
    code, out = run(capsys, "lint", "--format", "json", str(tmp_path / "s"))
    assert json.loads(out)[0]["severity"] == "warning"


def test_lint_installed_report(capsys):
    code, out = run(capsys, "lint", "--installed")
    assert code == 0 and "superpowers" in out and "harvested" in out
    code, out = run(capsys, "lint", "--installed", "--format", "json")
    assert json.loads(out)["superpowers"]["skills"] >= 1


def test_doctor_reports_skill_health(capsys):
    assert "skill health:" in run(capsys, "doctor")[1]


def test_eval_routing_command(capsys):
    code = cli.main(["eval", "routing"])
    out = capsys.readouterr().out
    assert code == 0 and "passed (100%)" in out and "data-engineer" in out


def test_eval_routing_reports_in_sample_and_holdout_apart(capsys, tmp_path):
    assert cli.main(["eval", "routing"]) == 0
    out = capsys.readouterr().out
    assert "in-sample:" in out and "holdout (never tuned on):" in out
    assert "FAIL" not in out.split("in-sample:")[1]  # holdout failures are not listed, so nobody tunes against them
    assert cli.main(["eval", "routing", "--format", "json"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["pass_rate"] == 1.0 and rep["holdout"]["cases"] >= 40
    (tmp_path / "c.yaml").write_text("cases:\n  - {id: x, role: qa-engineer, task: fix typo in README}\n")
    assert cli.main(["eval", "routing", "--cases", str(tmp_path / "c.yaml"), "--format", "json"]) == 0
    assert "holdout" not in json.loads(capsys.readouterr().out)


def test_eval_triggers_command(capsys):
    code = cli.main(["eval", "triggers"])
    out = capsys.readouterr().out
    assert code == 0 and "open-skill-router" in out and "holdout P" in out


def test_eval_triggers_lists_only_tuning_failures(capsys, tmp_path):
    (tmp_path / "s.yaml").write_text("skill: open-skill-learn\nqueries:\n"
                                     "  - {q: zzz tuning miss, trigger: true}\n"
                                     "  - {q: zzz holdout miss, trigger: true, holdout: true}\n")
    assert cli.main(["eval", "triggers", "--cases", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "missed: zzz tuning miss" in out and "zzz holdout miss" not in out


def test_eval_triggers_suggest(capsys, tmp_path):
    (tmp_path / "s.yaml").write_text("skill: open-skill-learn\nqueries:\n"
                                     "  - {q: qqq wibble one, trigger: true, holdout: false}\n"
                                     "  - {q: qqq wibble two, trigger: true, holdout: false}\n")
    assert cli.main(["eval", "triggers", "--cases", str(tmp_path), "--suggest"]) == 0
    assert "consider the concept behind: qqq (2), qqq wibble (2), wibble (2)" in capsys.readouterr().out


def test_eval_triggers_agent_needs_claude(capsys, monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert cli.main(["eval", "triggers", "--agent", "claude"]) == 2
    assert "claude CLI is not on PATH" in capsys.readouterr().err


def test_scan_agent_filter_and_unknown_agent(capsys):
    code, out = run(capsys, "scan", "--agent", "codex")
    assert code == 0 and "test-driven-development" in out and "superpowers:" not in out
    code, out = run(capsys, "scan")
    assert "claude-code,codex" in out  # agents column
    assert run(capsys, "scan", "--agent", "nope")[0] == 2


def test_agents_lists_detected_agents_and_their_skills(capsys):
    code, out = run(capsys, "agents")
    rows = {line.split()[1]: line for line in out.splitlines() if line[:1] in "✓·"}
    assert code == 0
    assert rows["claude-code"].startswith("✓") and rows["codex"].startswith("✓")
    assert rows["demo-agent"].startswith("·")
    code, out = run(capsys, "agents", "--json")
    by_id = {a["id"]: a for a in json.loads(out)}
    assert by_id["codex"]["detected"] is True and by_id["codex"]["skills"] >= 2
    assert by_id["codex"]["install_to"]["global"].endswith(".agents/skills")
    assert by_id["codex"]["install_to"]["project"] is None  # no --project given
    assert by_id["demo-agent"]["docs"].startswith("https://")


def test_install_dry_run_then_install_then_refuse(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    dest = tmp_path / "home/.agents/skills/open-skill-router"
    code, out = run(capsys, "install", "open-skill-router", "--agent", "codex", "--dry-run")
    assert code == 0 and out.startswith("would install") and not dest.exists()
    code, out = run(capsys, "install", "open-skill-router", "--agent", "codex")
    assert code == 0 and (dest / "SKILL.md").is_file() and str(dest) in out
    assert run(capsys, "install", "open-skill-router", "--agent", "codex")[1].startswith("unchanged")
    (dest / "SKILL.md").write_text("edited\n")
    assert run(capsys, "install", "open-skill-router", "--agent", "codex")[0] == 1
    assert (dest / "SKILL.md").read_text() == "edited\n"


def test_install_errors(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert run(capsys, "install", "open-skill-router", "--agent", "nope")[0] == 2
    assert run(capsys, "install", "no-such-skill", "--agent", "codex")[0] == 2
    code, _ = run(capsys, "install", "open-skill-learn", "--agent", "codex", "--project", str(tmp_path / "p"), "--symlink")
    assert code == 0 and (tmp_path / "p/.agents/skills/open-skill-learn").is_symlink()


def test_remove_only_what_install_created(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    dest = tmp_path / "home/.agents/skills/open-skill-router"
    run(capsys, "install", "open-skill-router", "--agent", "codex")
    (dest / "mine.md").write_text("mine\n")
    code, out = run(capsys, "remove", "open-skill-router", "--agent", "codex", "--dry-run")
    assert code == 0 and out.startswith("would remove") and (dest / "SKILL.md").exists()
    code, out = run(capsys, "remove", "open-skill-router", "--agent", "codex")
    assert code == 0 and "kept mine.md" in out
    assert (dest / "mine.md").exists() and not (dest / "SKILL.md").exists()
    assert run(capsys, "remove", "open-skill-router", "--agent", "codex")[0] == 1  # no longer ours
    assert run(capsys, "remove", "../../etc", "--agent", "codex")[0] == 2


def test_update_command(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert "no skills installed" in run(capsys, "update")[1]
    run(capsys, "install", "open-skill-learn", "--agent", "codex")
    code, out = run(capsys, "update", "--agent", "codex", "--dry-run")
    assert code == 0 and out.startswith("up to date: open-skill-learn for codex")
    assert run(capsys, "update", "--agent", "nope")[0] == 2


def test_route_agent_uses_names_valid_for_that_agent(capsys, tmp_path):
    (tmp_path / "p").mkdir()
    base = ["route", "fix the bug in the parser with tests", "--project", str(tmp_path / "p"), "--no-record"]
    r = json.loads(run(capsys, *base)[1])
    assert [s["invoke"] for s in r["chain"]] == ["superpowers:test-driven-development"] and r["agent"] is None
    r = json.loads(run(capsys, *base, "--agent", "codex")[1])
    assert [s["invoke"] for s in r["chain"]] == ["test-driven-development"] and r["agent"] == "codex"
    r = json.loads(run(capsys, *base, "--agent", "demo-agent")[1])
    assert r["chain"] == []  # demo-agent sees none of these skills
    assert run(capsys, *base, "--agent", "nope")[0] == 2


def test_search_agent_counts_only_that_agents_skills_as_installed(capsys):
    code, out = run(capsys, "search", "--installed", "--source", "superpowers", "--agent", "codex")
    assert code == 0 and "superpowers/test-driven-development" in out
    code, out = run(capsys, "search", "--installed", "--source", "harvested", "--agent", "codex")
    assert "harvested/my-internal-skill" not in out  # only in ~/.claude/skills
    assert "harvested/my-internal-skill" in run(capsys, "search", "--installed", "--source", "harvested")[1]
    assert run(capsys, "search", "x", "--agent", "nope")[0] == 2


def test_route_phase_flag(capsys, tmp_path):
    (tmp_path / "p").mkdir()
    base = ("route", "customers say the export returns nothing", "--project", str(tmp_path / "p"), "--no-record")
    code, out = run(capsys, *base, "--phase", "operate")
    assert code == 0 and json.loads(out)["target_phase"] == "operate" and json.loads(out)["phase_from"] == "given"
    code, out = run(capsys, *base, "--phase", "operate", "--explain")
    assert "target operate: given by the caller" in out
    assert run(capsys, *base, "--phase", "deploy")[0] == 2
