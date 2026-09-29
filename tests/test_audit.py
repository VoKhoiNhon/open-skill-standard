import re

import pytest

from open_skill import audit


@pytest.fixture
def toy_rule(monkeypatch):
    monkeypatch.setitem(audit.RULES, "toy", audit.Rule("toy", "medium", re.compile(r"danger"), "toy rule", "https://example.org"))


def test_audit_text_reports_line_and_excerpt(toy_rule):
    found = audit.audit_text("fine\n  here is danger  \n", "SKILL.md")
    assert [(f.rule, f.severity, f.file, f.line, f.excerpt) for f in found] == [("toy", "medium", "SKILL.md", 2, "here is danger")]
    assert found[0].source == "https://example.org"


def test_excerpt_escapes_control_and_invisible_characters(toy_rule):
    (f,) = audit.audit_text("danger\x1b[2J\u200b")
    assert f.excerpt == "danger\\x1b[2J\\u200b"


def test_excerpt_is_truncated(toy_rule):
    (f,) = audit.audit_text("danger " + "x" * 500)
    assert len(f.excerpt) <= 160 and f.excerpt.endswith("...")


def test_audit_paths_walks_every_file_and_sorts_by_severity(toy_rule, monkeypatch, tmp_path):
    monkeypatch.setitem(audit.RULES, "loud", audit.Rule("loud", "high", re.compile(r"LOUD"), "m", "s"))
    (tmp_path / "scripts").mkdir()
    (tmp_path / "SKILL.md").write_text("danger\n")
    (tmp_path / "scripts" / "run.sh").write_text("ok\nLOUD\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("danger\n")
    found = audit.audit_paths([tmp_path])
    assert [(f.rule, f.file) for f in found] == [("loud", str(tmp_path / "scripts" / "run.sh")),
                                                  ("toy", str(tmp_path / "SKILL.md"))]


def test_audit_paths_accepts_a_single_file(toy_rule, tmp_path):
    (tmp_path / "SKILL.md").write_text("danger\n")
    assert [f.line for f in audit.audit_paths([tmp_path / "SKILL.md"])] == [1]


def test_link_leaving_the_skill_is_reported_and_never_read(toy_rule, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("danger\n")
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "notes.md").symlink_to(outside)
    (skill / "linked-dir").symlink_to(tmp_path)
    found = audit.audit_paths([skill])
    assert sorted(f.file for f in found if f.rule == "link-outside-skill") == [str(skill / "linked-dir"), str(skill / "notes.md")]
    assert "toy" not in {f.rule for f in found}


def test_link_inside_the_skill_is_fine(toy_rule, tmp_path):
    (tmp_path / "a.md").write_text("ok\n")
    (tmp_path / "b.md").symlink_to(tmp_path / "a.md")
    assert audit.audit_paths([tmp_path]) == []


def test_a_linked_skill_folder_given_by_the_user_is_audited_at_its_target(toy_rule, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "SKILL.md").write_text("danger\n")
    (tmp_path / "installed").symlink_to(real)
    assert [f.rule for f in audit.audit_paths([tmp_path / "installed"])] == ["toy"]
