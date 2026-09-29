"""Every `open-skill` subcommand and flag, run as a subprocess against a temp home and a temp project.

`test_every_command_and_flag_is_exercised` reads this file and fails when `build_parser()` has a command, flag or
choice that no `cli.run(...)` call here passes, so a new flag cannot ship without an end-to-end test.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

from open_skill import __version__
from open_skill.cli import build_parser

REPO = Path(__file__).parents[1]
FIX = Path(__file__).parent / "fixtures"
SKIPPED_ENV = ("CLAUDECODE", "OPEN_SKILL_HOME", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "XDG_CONFIG_HOME")


class Cli:
    def __init__(self, tmp: Path):
        self.user = tmp / "user home"  # a space in every path the CLI touches
        shutil.copytree(FIX / "home", self.user)
        self.home = tmp / "open-skill home"
        self.project = tmp / "project dir"
        shutil.copytree(FIX / "project", self.project)
        self.tmp = tmp
        self.env = {k: v for k, v in os.environ.items() if k not in SKIPPED_ENV}
        self.env.update(HOME=str(self.user), USERPROFILE=str(self.user), OPEN_SKILL_HOME=str(self.home))

    def run(self, *argv: str, code: int = 0, stdin: str = "") -> subprocess.CompletedProcess:
        p = subprocess.run([sys.executable, "-m", "open_skill", *argv], capture_output=True, text=True,
                           encoding="utf-8", env=self.env, cwd=self.project, input=stdin)
        assert p.returncode == code, f"{argv}: exit {p.returncode}\nstdout: {p.stdout}\nstderr: {p.stderr}"
        if code == 0:
            assert p.stderr == "", f"{argv}: stderr on success: {p.stderr}"
        return p

    def json(self, *argv: str, code: int = 0):
        return json.loads(self.run(*argv, code=code).stdout)


@pytest.fixture
def cli(tmp_path):
    return Cli(tmp_path)


def _skill(folder: Path, name: str, body: str = "Steps to follow.\n", desc: str | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    desc = desc or f"Does {name} work for the user. Use when the user asks for {name}."
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n{body}", encoding="utf-8")
    return folder


# ---- documented JSON shapes ------------------------------------------------------------------------------------

def _documented_shapes() -> dict[str, tuple[str, list[str]]]:
    """README "JSON output" table: command -> (object | list, keys)."""
    text = (REPO / "README.md").read_text(encoding="utf-8")
    section = text.split("### JSON output", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| `open-skill ([^`]+)` \| (object|list of objects|object per \w+) \| ([^|]+) \|$", section, re.M)
    return {cmd: (kind, re.findall(r"`(\w[\w-]*)`", keys)) for cmd, kind, keys in rows}


def _check_shape(cmd: str, data) -> None:
    kind, keys = _documented_shapes()[cmd]
    if kind == "list of objects":
        assert isinstance(data, list)
        rows = data
    elif kind.startswith("object per"):
        assert isinstance(data, dict)
        rows = list(data.values())
    else:
        assert isinstance(data, dict)
        rows = [data]
    for row in rows:
        assert set(keys) <= set(row), f"{cmd}: missing {set(keys) - set(row)}"


def test_readme_documents_every_json_output():
    assert set(_documented_shapes()) == {
        "route", "scan --json", "agents --json", "status --json", "lint --format json",
        "lint --installed --format json", "audit --format json", "graph --format json",
        "eval routing --format json", "eval triggers --format json"}


# ---- registry and skill checks ---------------------------------------------------------------------------------

def test_version_and_validate(cli):
    assert cli.run("--version").stdout.strip() == f"open-skill {__version__}"
    assert cli.run("validate").stdout.strip() == "0 error(s)"
    assert cli.run("--registry", str(REPO), "validate").stdout.strip() == "0 error(s)"


def test_overlay_adds_skills(cli):
    out = cli.run("--registry", str(FIX / "repo"), "--overlay", str(FIX / "overlay"), "search", "--source", "acme").stdout
    assert "acme/" in out


def test_lint(cli):
    assert "0 error(s)" in cli.run("lint", str(REPO / "skills")).stdout
    bad = _skill(cli.tmp / "Bad Name", "Bad_Name")
    found = cli.json("lint", str(bad), "--format", "json", code=1)
    _check_shape("lint --format json", found)
    assert any(f["severity"] == "error" for f in found)
    loose = _skill(cli.tmp / "loose", "loose", body="".join(f"{i}. You MUST ALWAYS do this.\n" for i in range(7)))
    cli.run("lint", str(loose), "--format", "text")
    cli.run("lint", str(loose), "--strict", code=1)


def test_lint_installed(cli):
    report = cli.json("lint", "--installed", "--format", "json")
    _check_shape("lint --installed --format json", report)
    assert "source" in cli.run("lint", "--installed").stdout


def test_audit(cli):
    rep = cli.json("audit", str(FIX / "audit" / "clean-skill"), "--format", "json")
    _check_shape("audit --format json", rep)
    assert rep["summary"]["high"] == 0
    assert "high" in cli.run("audit", str(FIX / "audit" / "risky-skill"), code=1).stdout
    low = _skill(cli.tmp / "low", "low", body="Current branch: !`git branch --show-current`\n")
    assert "0 high, 0 medium, 1 low" in cli.run("audit", str(low), "--format", "text").stdout
    cli.run("audit", str(low), "--strict", code=1)
    rep = cli.json("audit", "--installed", "--project", str(cli.project), "--format", "json")
    assert rep["groups"]
    assert "no such file" in cli.run("audit", str(cli.tmp / "missing"), code=2).stderr


# ---- what is installed ----------------------------------------------------------------------------------------

def test_scan(cli):
    items = cli.json("scan", "--project", str(cli.project), "--json")
    _check_shape("scan --json", items)
    assert {"spec-kit/plan", "harvested/my-internal-skill"} <= {i["id"] for i in items}
    out = cli.run("scan", "--agent", "codex").stdout
    assert "test-driven-development" in out and "my-internal-skill" not in out
    assert "unknown agent" in cli.run("scan", "--agent", "nope", code=2).stderr


def test_scan_memory(cli):
    mem = cli.user / ".claude" / "projects" / "p" / "memory"
    mem.mkdir(parents=True)
    (mem / "tabs.md").write_text("---\nname: tabs\nmetadata:\n  type: feedback\n---\nIndent with tabs.\n", encoding="utf-8")
    assert cli.run("scan", "--memory").stdout.strip() == "imported 1 memory file(s)"
    assert cli.json("status", "--json")["notes"] == 1


def test_agents(cli):
    rows = cli.json("agents", "--project", str(cli.project), "--json")
    _check_shape("agents --json", rows)
    claude = next(r for r in rows if r["id"] == "claude-code")
    assert claude["detected"] and claude["install_to"]["project"].startswith(str(cli.project.resolve()))
    assert "agent(s) detected" in cli.run("agents").stdout


def test_install_remove_update(cli):
    out = cli.run("install", "open-skill-router", "--agent", "claude-code", "--dry-run").stdout
    assert out.startswith("would install") and not (cli.home / "installed.json").exists()
    cli.run("install", "open-skill-router", "--agent", "claude-code")
    dest = cli.user / ".claude" / "skills" / "open-skill-router"
    assert (dest / "SKILL.md").is_file()
    assert cli.run("install", "open-skill-router", "--agent", "claude-code").stdout.startswith("unchanged")
    cli.run("install", "open-skill-learn", "--agent", "codex", "--copy", "--project", str(cli.project))
    assert (cli.project / ".agents" / "skills" / "open-skill-learn" / "SKILL.md").is_file()
    assert "up to date" in cli.run("update", "--agent", "claude-code", "--dry-run").stdout
    assert "up to date" in cli.run("update").stdout
    assert cli.run("remove", "open-skill-router", "--agent", "claude-code", "--dry-run").stdout.startswith("would remove")
    assert dest.is_dir()
    cli.run("remove", "open-skill-router", "--agent", "claude-code")
    assert not dest.exists()
    cli.run("remove", "open-skill-learn", "--agent", "codex", "--project", str(cli.project))
    assert "not installed by open-skill" in cli.run("remove", "open-skill-router", "--agent", "claude-code", code=1).stderr
    assert "not a folder" in cli.run("install", "no-such-skill", "--agent", "claude-code", code=2).stderr
    assert "no skills installed" in cli.run("update", "--agent", "codex").stdout


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need developer mode on Windows; covered by test_install")
def test_install_symlink(cli):
    src = _skill(cli.tmp / "mine", "mine")
    out = cli.run("install", str(src), "--agent", "claude-code", "--symlink").stdout
    link = cli.user / ".claude" / "skills" / "mine"
    assert "(symlink)" in out and link.is_symlink()
    cli.run("remove", "mine", "--agent", "claude-code")
    assert not link.exists() and src.is_dir()


def test_install_refuses_a_different_skill(cli):
    _skill(cli.user / ".claude" / "skills" / "open-skill-router", "open-skill-router", body="Theirs.\n")
    err = cli.run("install", "open-skill-router", "--agent", "claude-code", code=1).stderr
    assert "never overwrites" in err


def test_build(cli):
    cli.run("build", "--check")
    root = cli.tmp / "build root"
    assert cli.run("build", "--root", str(root)).stdout.startswith("wrote")
    cli.run("build", "--root", str(root), "--check")
    (root / "dist" / "index.db").unlink()
    assert "stale" in cli.run("build", "--root", str(root), "--check", code=1).stderr


# ---- routing and search ---------------------------------------------------------------------------------------

def test_search(cli):
    out = cli.run("search", "test driven development", "--limit", "3", "--project", str(cli.project)).stdout
    assert 0 < len(out.splitlines()) <= 3
    out = cli.run("search", "--role", "data-engineer", "--phase", "build", "--source", "superpowers").stdout
    assert out and all("superpowers/" in line for line in out.splitlines())
    out = cli.run("search", "--installed", "--agent", "codex").stdout
    assert out and "(not installed)" not in out
    assert "unknown role" in cli.run("search", "--role", "nope", code=2).stderr
    assert "give a query" in cli.run("search", code=2).stderr


def test_route(cli):
    r = cli.json("route", "add a pipeline that loads orders", "--project", str(cli.project), "--role", "data-engineer",
                 "--size", "large", "--phase", "plan", "--model", "claude-opus-5-5", "--agent", "claude-code", "--no-record")
    _check_shape("route", r)
    assert r["target_phase"] == "plan" and r["phase_from"] == "given" and r["size"] == "large"
    assert not (cli.home / "events.jsonl").exists()
    assert cli.json("route", "rename a column", "--size", "small", "--no-record")["size"] == "small"
    assert cli.json("route", "rename a column", "--size", "medium", "--no-record")["size"] == "medium"
    out = cli.run("route", "fix the failing login test", "--explain", "--no-record").stdout
    assert out.startswith("route r-") and "score=" in out
    out = cli.run("route", "add a pipeline", "--role", "data-engineer", "--why-not", "spec-kit/plan", "--no-record").stdout
    assert "spec-kit/plan" in out
    assert "unknown phase" in cli.run("route", "x", "--phase", "nope", code=2).stderr
    r = cli.json("route", "add a pipeline that loads orders")
    events = (cli.home / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(events[-1])["route_id"] == r["route_id"]


def test_graph(cli):
    assert cli.run("graph").stdout == cli.run("graph", "--format", "mermaid").stdout
    assert cli.run("graph").stdout.startswith("graph LR")
    g = cli.json("graph", "--format", "json")
    _check_shape("graph --format json", g)
    page = cli.tmp / "out dir" / "graph.html"
    page.parent.mkdir()
    assert cli.run("graph", "--format", "html", "--out", str(page)).stdout.startswith("wrote")
    assert page.read_text(encoding="utf-8").lstrip().lower().startswith("<!doctype html")


def test_doctor(cli):
    out = cli.run("doctor", "--project", str(cli.project)).stdout
    assert out.startswith(f"open-skill {__version__}") and "no profile yet" in out


# ---- the user layer -------------------------------------------------------------------------------------------

def test_init_learn_forget_status(cli):
    cli.run("init", "--role", "data-engineer=0.7", "--role", "data-analyst", "--stack", "python",
            "--framework", "spec-kit", "--language", "en")
    cli.run("init", "--role", "data-engineer", "--framework", "bmad-method")
    cli.run("init", "--role", "data-engineer", "--framework", "superpowers")
    prof = yaml.safe_load((cli.home / "profile.yaml").read_text(encoding="utf-8"))
    assert prof["roles"] == {"data-engineer": 1.0} and prof["build_framework"] == "superpowers"
    assert "unknown role" in cli.run("init", "--role", "nope", code=2).stderr
    ids = [cli.run("learn", "Tabs, not spaces.", "--applies-to", "role:*", "--type", "preference").stdout,
           cli.run("learn", "Retry once.", "--applies-to", "role:*", "--type", "lesson").stdout,
           cli.run("learn", "SCD: slowly changing dimension.", "--applies-to", "role:*", "--type", "glossary").stdout,
           cli.run("learn", "Orders land at 02:00.", "--applies-to", "project:.", "--type", "project-fact").stdout,
           cli.run("learn", "Never trust row counts.", "--applies-to", "role:*", "--type", "pitfall").stdout]
    ids = [i.strip() for i in ids]
    assert len(set(ids)) == 5
    assert "looks like" in cli.run("learn", "password: hunter2", "--applies-to", "role:*", code=2).stderr
    cli.run("learn", "password: hunter2", "--applies-to", "role:*", "--force")
    info = cli.json("status", "--json")
    _check_shape("status --json", info)
    seeds = sum(len(yaml.safe_load((REPO / "registry" / "roles" / f"{r}.yaml").read_text(encoding="utf-8"))["seeds"])
                for r in ("data-engineer", "data-analyst"))  # re-running init keeps earlier roles' seeds
    assert info["notes"] == seeds + 6 and info["pending_migrations"] == 0
    assert cli.run("forget", ids[0]).stdout.strip() == "forgotten"
    assert cli.run("forget", ids[0], code=1).stdout.strip() == "not found"
    assert "data_schema" in cli.run("status").stdout


def test_feedback_and_export(cli):
    rid = cli.json("route", "add tests for the parser")["route_id"]
    cli.run("feedback", rid, "--ran", "superpowers:test-driven-development", "--outcome", "ok", "--note", "fine")
    cli.run("feedback", rid, "--outcome", "fail")
    events = [json.loads(line) for line in (cli.home / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [e["outcome"] for e in events if e["type"] == "feedback"] == ["ok", "fail"]
    cli.run("learn", "Keep functions short.", "--applies-to", "role:*")
    out = Path(cli.run("export", str(cli.tmp / "exports" / "mine.zip")).stdout.strip())
    names = zipfile.ZipFile(out).namelist()
    assert any(n.startswith("knowledge/") for n in names) and not any("events" in n for n in names)


def test_backup_restore(cli):
    assert "nothing to back up" in cli.run("backup").stdout
    nid = cli.run("learn", "Prefer small commits.", "--applies-to", "role:*").stdout.strip()
    archive = Path(cli.run("backup").stdout.strip())
    assert cli.run("backup", "--list").stdout.strip() == str(archive)
    note = cli.home / "knowledge" / f"{nid}.md"
    before = note.read_bytes()
    cli.run("forget", nid)
    assert "previous state saved" in cli.run("restore", str(archive)).stdout
    assert note.read_bytes() == before
    evil = cli.tmp / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../escape.txt", "x")
    assert "unsafe" in cli.run("restore", str(evil), code=2).stderr


def _legacy_home(cli) -> Path:
    """A v0 layout: notes without schema stamps, no VERSION file."""
    k = cli.home / "knowledge"
    k.mkdir(parents=True)
    note = k / "k-old-1.md"
    note.write_text("---\nid: k-old-1\nkind: knowledge\ntype: lesson\napplies_to: [role:*]\nsource: user\n"
                    "created: '2026-01-01'\n---\nOld   text, kept  byte for byte.\n", encoding="utf-8")
    return note


def test_migrate(cli):
    note = _legacy_home(cli)
    body = note.read_text(encoding="utf-8").split("---\n", 2)[2]
    out = cli.run("migrate", "--dry-run").stdout
    assert out.startswith("dry run") and "schema" not in note.read_text(encoding="utf-8")
    cli.run("migrate")
    assert note.read_text(encoding="utf-8").endswith(body) and "schema: 1" in note.read_text(encoding="utf-8")
    assert "up to date" in cli.run("migrate").stdout


def test_seeds(cli):
    assert cli.run("seeds", "sync", code=1).stdout.startswith("no roles")
    cli.run("init", "--role", "data-engineer")
    assert cli.run("seeds", "sync").stdout.strip() == "starter knowledge is up to date"
    sid = "data-engineer/use-merge-business-key-instead"
    note = next(p for p in (cli.home / "knowledge").glob("*.md") if sid in p.read_text(encoding="utf-8"))
    note.write_text(note.read_text(encoding="utf-8").replace("blind INSERT.", "blind INSERT, my way."), encoding="utf-8")
    overlay = cli.tmp / "overlay"
    (overlay / "roles").mkdir(parents=True)
    role = yaml.safe_load((REPO / "registry" / "roles" / "data-engineer.yaml").read_text(encoding="utf-8"))
    role["seeds"][0]["text"] = "Use MERGE on the business key; never a blind INSERT."
    (overlay / "roles" / "data-engineer.yaml").write_text(yaml.safe_dump(role), encoding="utf-8")
    assert "would" in cli.run("--overlay", str(overlay), "seeds", "sync", "--dry-run").stdout
    assert "kept your edit" in cli.run("--overlay", str(overlay), "seeds", "sync").stdout
    assert "(upstream)" in cli.run("seeds", "diff").stdout
    assert "(upstream)" in cli.run("seeds", "diff", sid).stdout
    cli.run("seeds", "keep", sid)
    assert "my way" in note.read_text(encoding="utf-8")
    assert "no seed updates" in cli.run("seeds", "keep").stdout
    role["seeds"][0]["text"] = "Use MERGE on the business key. Blind INSERTs duplicate rows."
    (overlay / "roles" / "data-engineer.yaml").write_text(yaml.safe_dump(role), encoding="utf-8")
    cli.run("--overlay", str(overlay), "seeds", "sync")
    assert "your version is in" in cli.run("seeds", "accept", sid).stdout
    assert "duplicate rows" in note.read_text(encoding="utf-8")
    assert "no proposal" in cli.run("seeds", "accept", "data-engineer/nope", code=1).stderr


def test_upgrade_and_rollback(cli):
    assert "no pre-upgrade backup" in cli.run("upgrade", "--rollback", code=1).stderr
    note = _legacy_home(cli)
    (cli.home / "profile.yaml").write_text("roles:\n  data-engineer: 1.0\n", encoding="utf-8")
    before = {p.relative_to(cli.home).as_posix(): p.read_bytes() for p in cli.home.rglob("*") if p.is_file()}
    out = cli.run("upgrade", "--dry-run").stdout
    assert out.startswith("dry run") and "would add" in out
    assert {p.relative_to(cli.home).as_posix(): p.read_bytes() for p in cli.home.rglob("*") if p.is_file()} == before
    out = cli.run("upgrade").stdout
    assert "backed up to" in out and "schema: 1" in note.read_text(encoding="utf-8")
    assert "restored" in cli.run("upgrade", "--rollback").stdout
    after = {p.relative_to(cli.home).as_posix(): p.read_bytes() for p in cli.home.rglob("*")
             if p.is_file() and not p.relative_to(cli.home).as_posix().startswith("backups/")}
    assert after == before


def test_newer_data_is_refused_with_exit_3(cli):
    cli.home.mkdir()
    (cli.home / "VERSION").write_text("99\n", encoding="utf-8")
    assert "newer" in cli.run("learn", "x", "--applies-to", "role:*", code=3).stderr
    assert cli.json("status", "--json")["data_schema"] == 99


# ---- evals and adapters ---------------------------------------------------------------------------------------

def test_eval_routing(cli):
    cases = cli.tmp / "cases.yaml"
    data = yaml.safe_load((REPO / "evals" / "routing.yaml").read_text(encoding="utf-8"))
    cases.write_text(yaml.safe_dump({"cases": data["cases"][:3]}), encoding="utf-8")
    rep = cli.json("eval", "routing", "--cases", str(cases), "--format", "json")
    _check_shape("eval routing --format json", rep)
    assert rep["cases"] == 3 and "holdout" not in rep
    assert "in-sample: 3/3" in cli.run("eval", "routing", "--cases", str(cases), "--format", "text").stdout


def test_eval_triggers(cli):
    rep = cli.json("eval", "triggers", "--cases", str(FIX / "triggers"), "--format", "json")
    _check_shape("eval triggers --format json", rep)
    assert "consider the concept" in cli.run("eval", "triggers", "--suggest").stdout
    assert "claude CLI is not on PATH" in cli.run("eval", "triggers", "--agent", "claude", code=2).stderr


@pytest.mark.skipif(sys.platform == "win32", reason="the stand-in agent is a POSIX shell script")
def test_eval_triggers_with_an_agent(cli):
    bin_dir = cli.tmp / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "claude"
    event = {"message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "open-skill:demo"}}]}}
    fake.write_text(f"#!/bin/sh\necho '{json.dumps(event)}'\n", encoding="utf-8")
    fake.chmod(0o755)
    cli.env["PATH"] = f"{bin_dir}{os.pathsep}{cli.env['PATH']}"
    rep = cli.json("eval", "triggers", "--cases", str(FIX / "triggers"), "--agent", "claude", "--runs", "1",
                   "--format", "json")
    assert rep["demo-skill"]["train"]["recall"] == 1.0 or rep["demo-skill"]["validation"]["recall"] == 1.0
    assert "agent run: claude, 1 runs" in cli.run("eval", "triggers", "--cases", str(FIX / "triggers"),
                                                  "--agent", "claude", "--runs", "1").stdout


def test_adapter(cli):
    up = FIX / "upstream" / "skills"
    draft = yaml.safe_load(cli.run("adapter", "draft", "--source", "demo", "--from", str(up)).stdout)
    assert {s["name"] for s in draft["skills"]} == {"test-driven-development", "new-one"}
    out = cli.run("adapter", "check", "--source", "superpowers", "--from", str(up), code=1).stdout
    assert "+ new-one" in out
    ok = cli.tmp / "up"
    for s in yaml.safe_load((REPO / "registry" / "adapters" / "ponytail.yaml").read_text(encoding="utf-8"))["skills"]:
        _skill(ok / s["name"], s["name"])
    cli.run("adapter", "check", "--source", "ponytail", "--from", str(ok))


# ---- every command, flag and choice has a test above ----------------------------------------------------------

def _parser_surface() -> set[str]:
    """`cmd`, `cmd --flag` and `cmd choice` (for flags and positionals with choices), plus global flags."""
    parser = build_parser()
    want = {f"{o}" for a in parser._actions for o in a.option_strings if o not in ("-h", "--help")}
    sub = next(a for a in parser._actions if isinstance(a, type(parser._subparsers._group_actions[0])))
    for cmd, sp in sub.choices.items():
        want.add(cmd)
        for a in sp._actions:
            flags = [o for o in a.option_strings if o.startswith("--") and o != "--help"]
            want |= {f"{cmd} {flags[0]}"} if flags else set()
            for c in a.choices or []:
                want.add(f"{cmd} {flags[0] if flags else ''} {c}".replace("  ", " "))
    return want


def _exercised() -> set[str]:
    commands = set(next(a for a in build_parser()._actions if a.dest == "cmd").choices)
    seen = set()
    for node in ast.walk(ast.parse(Path(__file__).read_text(encoding="utf-8"))):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("run", "json")
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "cli"):
            continue
        args = [a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else None for a in node.args]
        cmd_at = next((i for i, a in enumerate(args) if a in commands), None)
        seen |= {a for a in args[: cmd_at if cmd_at is not None else len(args)] if a and a.startswith("--")}
        if cmd_at is None:
            continue
        cmd, prev = args[cmd_at], None
        seen.add(cmd)
        for a in args[cmd_at + 1:]:
            if a and a.startswith("--"):
                seen.add(f"{cmd} {a}")
            elif a:
                seen.add(f"{cmd} {prev} {a}" if prev and prev.startswith("--") else f"{cmd} {a}")
            prev = a
    return seen


def test_every_command_and_flag_is_exercised():
    missing = sorted(_parser_surface() - _exercised())
    assert not missing, f"no end-to-end test passes: {missing}"
