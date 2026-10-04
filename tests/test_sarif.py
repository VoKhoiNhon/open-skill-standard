from pathlib import Path

from open_skill import __version__, sarif

RULES = [{"id": "a", "severity": "high", "text": "rule a", "source": "https://example.com/a", "security": True},
         {"id": "b", "severity": "warning", "text": "rule b", "source": "https://example.com/b"}]


def test_log_has_the_tool_rules_and_levels(tmp_path):
    doc = sarif.log(RULES, [{"rule": "b", "severity": "warning", "message": "m", "path": "x/SKILL.md"}], tmp_path)
    (run,) = doc["runs"]
    driver = run["tool"]["driver"]
    assert driver["name"] == "open-skill" and driver["version"] == __version__
    assert [r["defaultConfiguration"]["level"] for r in driver["rules"]] == ["error", "warning"]
    assert driver["rules"][0]["properties"] == {"tags": ["security"], "security-severity": "8.0"}
    assert "security-severity" not in driver["rules"][1]["properties"]
    (res,) = run["results"]
    assert res["ruleIndex"] == 1 and res["level"] == "warning" and res["message"] == {"text": "m"}


def test_paths_inside_the_base_are_relative_and_others_are_file_uris(tmp_path):
    inside, outside = tmp_path / "base" / "my skill" / "SKILL.md", tmp_path / "elsewhere" / "SKILL.md"
    doc = sarif.log(RULES, [{"rule": "a", "severity": "high", "message": "m", "path": str(p), "line": 3,
                             "snippet": "x"} for p in (inside, outside)], tmp_path / "base")
    first, second = (r["locations"][0]["physicalLocation"] for r in doc["runs"][0]["results"])
    assert first["artifactLocation"] == {"uri": "my%20skill/SKILL.md", "uriBaseId": "SRCROOT"}
    assert first["region"] == {"startLine": 3, "snippet": {"text": "x"}}
    assert second["artifactLocation"] == {"uri": outside.as_uri()}
    assert doc["runs"][0]["originalUriBaseIds"]["SRCROOT"]["uri"] == (tmp_path / "base").resolve().as_uri() + "/"


def test_file_level_findings_have_no_region(tmp_path):
    doc = sarif.log(RULES, [{"rule": "a", "severity": "high", "message": "m", "path": "bin/tool", "line": 0}], tmp_path)
    assert "region" not in doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]


def test_unknown_rule_ids_have_no_rule_index(tmp_path):
    doc = sarif.log(RULES, [{"rule": "zzz", "severity": "error", "message": "m", "path": Path("p").as_posix()}], tmp_path)
    assert "ruleIndex" not in doc["runs"][0]["results"][0]


def test_relative_paths_are_normalized_from_the_current_folder(tmp_path, monkeypatch):
    (tmp_path / "repo" / "s").mkdir(parents=True)
    monkeypatch.chdir(tmp_path / "repo")
    doc = sarif.log(RULES, [{"rule": "b", "severity": "warning", "message": "m", "path": p}
                            for p in ("./s/../s/SKILL.md", "../other/SKILL.md")])
    first, second = (r["locations"][0]["physicalLocation"]["artifactLocation"] for r in doc["runs"][0]["results"])
    assert first == {"uri": "s/SKILL.md", "uriBaseId": "SRCROOT"}
    assert second == {"uri": (tmp_path / "other" / "SKILL.md").resolve().as_uri()}
