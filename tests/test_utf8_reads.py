"""Skill files, manifests and memory notes are UTF-8 whatever the locale code page (cp1252 on most Windows setups)."""

import json

from open_skill import knowledge, lint, scan

DESC = "Tóm tắt tài liệu — dùng khi cần “bản ngắn”."


def skill(folder, name=None, description=DESC):
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / "SKILL.md"
    p.write_text(f"---\nname: {name or folder.name}\ndescription: {description}\n---\nBody.\n", encoding="utf-8")
    return p


def test_scan_reads_the_description_as_utf8(tmp_path):
    assert scan._describe(skill(tmp_path / "summarize")) == ("summarize", DESC)


def test_lint_matches_a_non_ascii_name_to_its_folder(tmp_path):
    rules = {f.rule for f in lint.lint_file(skill(tmp_path / "tóm-tắt"))}
    assert "name-matches-folder" not in rules


def test_lint_reads_a_manifest_as_utf8(tmp_path):
    p = tmp_path / "plugin.json"
    p.write_text(json.dumps({"name": "tools", "description": DESC}, ensure_ascii=False), encoding="utf-8")
    doc, why = lint._load_manifest(p)
    assert why is None and doc["description"] == DESC


def test_agent_memory_is_imported_as_utf8(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "home"))
    note = tmp_path / "projects" / "p" / "memory" / "fact.md"
    note.parent.mkdir(parents=True)
    note.write_text("---\ntype: project\n---\nDữ liệu ngày được lưu theo giờ UTC.\n", encoding="utf-8")
    assert knowledge.import_agent_memory(tmp_path / "projects") == 1
    assert [n["text"] for n in knowledge.load_knowledge()] == ["Dữ liệu ngày được lưu theo giờ UTC."]
