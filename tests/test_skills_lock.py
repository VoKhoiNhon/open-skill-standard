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
    assert skills_lock.check(LOCKED, DIRS) == {"ok": ["demo"], "changed": ["edited"], "missing": ["gone"],
                                               "unchecked": []}


def test_hash_skips_git_and_node_modules(tmp_path):
    shutil.copytree(LOCKED / ".agents/skills/demo", tmp_path / "demo")
    before = skills_lock.folder_hash(tmp_path / "demo")
    for extra in ("node_modules/x/index.js", ".git/HEAD", "scripts/__pycache__/run.cpython-313.pyc"):
        (tmp_path / "demo" / extra).parent.mkdir(parents=True)
        (tmp_path / "demo" / extra).write_text("x", encoding="utf-8")
    assert skills_lock.folder_hash(tmp_path / "demo") == before


@pytest.mark.parametrize("text", ["", "{", "[]", '{"version": 0, "skills": {}}', '{"version": 1}',
                                  '{"version": true, "skills": {}}',
                                  '{"version": "1", "skills": {}}', '{"version": 1, "skills": []}'])
def test_unreadable_or_old_locks_are_ignored(tmp_path, text):
    (tmp_path / "skills-lock.json").write_text(text, encoding="utf-8")
    assert skills_lock.read(tmp_path) is None and skills_lock.check(tmp_path, DIRS) is None


def test_no_lock_means_no_check(tmp_path):
    assert skills_lock.check(tmp_path, DIRS) is None


def test_lock_names_are_never_paths(tmp_path):
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "SKILL.md").write_text("x", encoding="utf-8")
    lock = {"version": 1, "skills": {"../../outside": {"computedHash": "0"}, "C:outside": {"computedHash": "0"},
                                     "ok": {"computedHash": "0"}}}
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "skills-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    assert skills_lock.check(tmp_path / "p", DIRS) == {"ok": [], "changed": [], "missing": ["ok"], "unchecked": []}


def test_doctor_reports_the_lock(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    cli.main(["doctor", "--project", str(LOCKED)])
    (line,) = [x for x in capsys.readouterr().out.splitlines() if "skills-lock.json" in x]
    assert "3 skill(s) installed by npx skills" in line and "skills-lock.json: " in line
    assert "1 differ from the lock (edited, or installed without some files) → npx skills update (edited)" in line and "1 not in a skill folder (gone)" in line


def test_non_ascii_file_names_are_unchecked_not_changed(tmp_path):
    # localeCompare orders accented, CJK and emoji names by Unicode collation tables Python does not ship, so a hash
    # over them could differ from npx skills' and call an untouched skill edited.
    shutil.copytree(LOCKED / ".agents/skills/demo", tmp_path / ".agents/skills/demo")
    (tmp_path / ".agents/skills/demo/references/ghi-chú.md").write_text("x", encoding="utf-8")
    lock = {"version": 1, "skills": {"demo": {"computedHash": "0" * 64}}}
    (tmp_path / "skills-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    assert skills_lock.folder_hash(tmp_path / ".agents/skills/demo") is None
    assert skills_lock.check(tmp_path, DIRS)["unchecked"] == ["demo"]


def test_an_unreadable_file_is_unchecked_not_a_crash(tmp_path, monkeypatch):
    shutil.copytree(LOCKED / ".agents/skills/demo", tmp_path / "demo")

    def refuse(self):
        raise PermissionError(13, "Permission denied", str(self))
    monkeypatch.setattr(Path, "read_bytes", refuse)
    assert skills_lock.folder_hash(tmp_path / "demo") is None


def test_lock_is_found_up_to_the_repository_root(tmp_path):
    # npx skills writes the lock where it runs, usually the repository root; doctor may run from a subfolder.
    repo = tmp_path / "repo"
    shutil.copytree(LOCKED, repo)
    (repo / ".git").mkdir()
    (repo / "src" / "app").mkdir(parents=True)
    assert skills_lock.find(repo / "src" / "app") == repo.resolve()
    assert skills_lock.find(repo) == repo.resolve()


def test_lock_is_not_searched_above_the_repository_root(tmp_path):
    shutil.copytree(LOCKED, tmp_path / "outer")
    (tmp_path / "outer" / "repo" / ".git").mkdir(parents=True)
    assert skills_lock.find(tmp_path / "outer" / "repo") is None


def test_lock_outside_a_repository_is_only_read_in_the_folder_itself(tmp_path):
    shutil.copytree(LOCKED, tmp_path / "p")
    (tmp_path / "p" / "sub").mkdir()
    assert skills_lock.find(tmp_path / "p" / "sub") is None
    assert skills_lock.find(tmp_path / "p") == (tmp_path / "p").resolve()


def test_doctor_reads_the_lock_at_the_repository_root(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    repo = tmp_path / "repo"
    shutil.copytree(LOCKED, repo)
    (repo / ".git").mkdir()
    (repo / "pkg").mkdir()
    cli.main(["doctor", "--project", str(repo / "pkg")])
    (line,) = [x for x in capsys.readouterr().out.splitlines() if "skills-lock.json" in x]
    assert "3 skill(s) installed by npx skills" in line and "1 not in a skill folder (gone)" in line
    assert f"skills-lock.json (in {repo.resolve()}):" in line
