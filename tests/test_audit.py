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
    (f,) = audit.audit_text("danger\x1b[2J​")
    assert f.excerpt == "danger\\x1b[2J\\u200b"


def test_excerpt_is_truncated(toy_rule):
    (f,) = audit.audit_text("danger " + "x" * 500)
    assert len(f.excerpt) <= 160 and f.excerpt.endswith("...")
