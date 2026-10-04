import json
import shutil
from pathlib import Path

import pytest

from open_skill import cli, skills_lock

LOCKED = Path(__file__).parent / "fixtures" / "skills-lock"
DIRS = [".agents/skills", ".claude/skills"]


def test_folder_hash_matches_npx_skills():
    # The lock's hashes were computed by vercel-labs/skills' own computeSkillFolderHash. Its files sort with
    # localeCompare, so references/ comes before SKILL.md and a-b.md before a_b.md... unlike a code point sort.
    lock = skills_lock.read(LOCKED)
    assert skills_lock.folder_hash(LOCKED / ".agents/skills/demo") == lock["demo"]["computedHash"]


def test_check_tells_as_installed_from_edited_and_missing():
    assert skills_lock.check(LOCKED, DIRS) == {"ok": ["demo"], "changed": ["edited"], "missing": ["gone"]}


def test_hash_skips_git_and_node_modules(tmp_path):
    shutil.copytree(LOCKED / ".agents/skills/demo", tmp_path / "demo")
    before = skills_lock.folder_hash(tmp_path / "demo")
    for extra in ("node_modules/x/index.js", ".git/HEAD"):
        (tmp_path / "demo" / extra).parent.mkdir(parents=True)
        (tmp_path / "demo" / extra).write_text("x", encoding="utf-8")
    assert skills_lock.folder_hash(tmp_path / "demo") == before


@pytest.mark.parametrize("text", ["", "{", "[]", '{"version": 0, "skills": {}}', '{"version": 1}',
                                  '{"version": "1", "skills": {}}', '{"version": 1, "skills": []}'])
def test_unreadable_or_old_locks_are_ignored(tmp_path, text):
    (tmp_path / "skills-lock.json").write_text(text, encoding="utf-8")
    assert skills_lock.read(tmp_path) is None and skills_lock.check(tmp_path, DIRS) is None


def test_no_lock_means_no_check(tmp_path):
    assert skills_lock.check(tmp_path, DIRS) is None


def test_lock_names_are_never_paths(tmp_path):
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "SKILL.md").write_text("x", encoding="utf-8")
    lock = {"version": 1, "skills": {"../../outside": {"computedHash": "0"}, "ok": {"computedHash": "0"}}}
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "skills-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    assert skills_lock.check(tmp_path / "p", DIRS) == {"ok": [], "changed": [], "missing": ["ok"]}


def test_doctor_reports_the_lock(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    cli.main(["doctor", "--project", str(LOCKED)])
    (line,) = [x for x in capsys.readouterr().out.splitlines() if "skills-lock.json" in x]
    assert "3 skill(s) installed by npx skills" in line
    assert "1 changed since install (edited)" in line and "1 not in a skill folder (gone)" in line
