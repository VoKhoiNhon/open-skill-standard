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


@pytest.mark.parametrize("argv", [["audit", "--installed"], ["audit"]])
def test_audit_installed_groups_by_source(capsys, argv):
    code, out = run(capsys, *argv)
    assert code == 0
    assert "== harvested" in out and "== superpowers" in out
    assert "claude-code-builtin" not in out  # built-in skills have no files to read


def test_audit_json_has_groups_summary_and_disclaimer(capsys):
    import json

    code, out = run(capsys, "audit", str(AUDIT / "risky-skill"), "--format", "json")
    doc = json.loads(out)
    assert doc["disclaimer"] == audit.DISCLAIMER
    (found,) = doc["groups"].values()
    assert {"severity", "rule", "file", "line", "excerpt", "source", "message"} <= set(found[0])
    assert doc["summary"]["high"] == sum(1 for f in found if f["severity"] == "high") > 0


def test_audit_exit_code_fails_on_high_severity(capsys):
    assert run(capsys, "audit", str(AUDIT / "risky-skill"))[0] == 1
    assert run(capsys, "audit", str(AUDIT / "risky-skill"), "--format", "json")[0] == 1


def test_audit_strict_fails_on_any_finding(capsys, tmp_path):
    (tmp_path / "SKILL.md").write_text("- Changes: !`git status`\n")  # one low-severity finding
    assert run(capsys, "audit", str(tmp_path))[0] == 0
    assert run(capsys, "audit", str(tmp_path), "--strict")[0] == 1
    assert run(capsys, "audit", str(AUDIT / "clean-skill"), "--strict")[0] == 0


def test_doctor_shows_a_one_line_audit_summary(capsys):
    code, out = run(capsys, "doctor")
    (line,) = [x for x in out.splitlines() if "security audit" in x]
    assert "0 high, 0 medium, 0 low" in line and "open-skill audit --installed" in line
