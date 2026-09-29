from pathlib import Path

import pytest

from open_skill import audit, cli

FIX = Path(__file__).parent / "fixtures"
AUDIT = FIX / "audit"


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))
    monkeypatch.setenv("HOME", str(FIX / "home"))


def run(capsys, *argv):
    code = cli.main(["--registry", str(FIX / "repo"), *argv])
    return code, capsys.readouterr().out


def test_audit_paths_prints_findings_and_the_disclaimer(capsys):
    code, out = run(capsys, "audit", str(AUDIT / "risky-skill"))
    assert "[override-instructions]" in out and "risky-skill/SKILL.md:" in out
    assert "https://genai.owasp.org/llmrisk/llm01-prompt-injection/" in out
    assert audit.DISCLAIMER in out


def test_audit_clean_skill_says_no_rule_matched(capsys):
    code, out = run(capsys, "audit", str(AUDIT / "clean-skill"))
    assert code == 0 and "0 high, 0 medium, 0 low" in out and audit.DISCLAIMER in out


def test_audit_missing_path_is_an_error(capsys, tmp_path):
    assert cli.main(["audit", str(tmp_path / "nope")]) == 2
