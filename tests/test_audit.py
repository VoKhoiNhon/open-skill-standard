import re
from pathlib import Path

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


@pytest.mark.parametrize("head", [b"\x7fELF\x02\x01", b"\xcf\xfa\xed\xfe\x07\x00", b"MZ\x90\x00\x03\x00"])
def test_bundled_native_executable_is_flagged(toy_rule, tmp_path, head):
    (tmp_path / "tool").write_bytes(head + b"\0" * 64 + b"danger")
    assert [f.rule for f in audit.audit_paths([tmp_path])] == ["native-executable"]


def test_other_binary_assets_are_skipped(toy_rule, tmp_path):
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\0\0danger")
    assert audit.audit_paths([tmp_path]) == []


def test_oversized_text_is_reported_as_unscanned(toy_rule, tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "MAX_TEXT_BYTES", 100)
    (tmp_path / "big.md").write_text("x" * 200 + "\ndanger\n")
    assert [(f.rule, f.severity) for f in audit.audit_paths([tmp_path])] == [("unscanned-file", "low")]


def test_special_files_are_skipped_without_opening(toy_rule, tmp_path):
    import os

    os.mkfifo(tmp_path / "pipe")  # opening a FIFO for reading would block the audit forever
    assert audit.audit_paths([tmp_path]) == []


FIXTURES = Path(__file__).parent / "fixtures" / "audit"


def test_clean_fixture_skill_has_no_findings():
    assert audit.audit_paths([FIXTURES / "clean-skill"]) == []


def test_every_line_rule_matches_the_risky_fixture():
    fired = {f.rule for f in audit.audit_paths([FIXTURES / "risky-skill"])}
    assert {r.id for r in audit.RULES.values() if r.pattern} <= fired
