from pathlib import Path

import yaml

from open_skill import registry

FIX = Path(__file__).parent / "fixtures"


def test_load_flattens_adapter_skills():
    reg = registry.load(FIX / "repo")
    s = reg.skills["superpowers/test-driven-development"]
    assert s["source"] == "superpowers"
    assert s["install"] == {"skills-cli": "npx skills add obra/superpowers -g"}
    assert s["portability"] == ["claude-code", "codex"]
    assert "spec-kit/implement" in reg.skills
    assert reg.roles["data-engineer"]["family"] == "data-ai" and "data-analyst" in reg.roles
    assert set(reg.models) == {"generic", "claude-opus-5", "claude-opus-5-5", "claude-haiku-4-5"}


def test_overlay_adds_skill_and_overrides_role():
    reg = registry.load(FIX / "repo", overlays=[FIX / "overlay"])
    assert "acme/warehouse-audit" in reg.skills
    assert reg.roles["data-engineer"]["risk"] == "Overridden by org"
    assert reg.roles["data-engineer"]["name"] == "Data Engineer"


def test_fixture_is_valid():
    assert registry.validate(registry.load(FIX / "repo")) == []


def test_validate_reports_dangling_role_reference(tmp_path):
    root = tmp_path / "r"
    (root / "registry").mkdir(parents=True)
    import shutil
    shutil.copytree(FIX / "repo" / "registry", root / "registry", dirs_exist_ok=True)
    role = yaml.safe_load((root / "registry/roles/data-engineer.yaml").read_text())
    role["phases"]["build"]["primary"] = ["superpowers/does-not-exist"]
    (root / "registry/roles/data-engineer.yaml").write_text(yaml.safe_dump(role))
    errors = registry.validate(registry.load(root))
    assert any("superpowers/does-not-exist" in e for e in errors)


def test_validate_reports_dangling_alternative_and_schema_error(tmp_path):
    root = tmp_path / "r"
    import shutil
    shutil.copytree(FIX / "repo", root)
    p = root / "registry/adapters/superpowers.yaml"
    doc = yaml.safe_load(p.read_text())
    doc["skills"][0]["alternatives"] = ["nobody/missing"]
    doc["skills"][1]["phases"] = ["not-a-phase"]
    p.write_text(yaml.safe_dump(doc))
    errors = registry.validate(registry.load(root))
    assert any("nobody/missing" in e for e in errors)
    assert any("not-a-phase" in e for e in errors)


def test_validate_requires_seed_ids(tmp_path):
    import shutil
    root = tmp_path / "r"
    shutil.copytree(FIX / "repo", root)
    p = root / "registry/roles/data-engineer.yaml"
    doc = yaml.safe_load(p.read_text())
    doc["seeds"] = ["no id here", {"id": "a", "text": "x"}, {"id": "a", "text": "y"}]
    p.write_text(yaml.safe_dump(doc))
    errors = registry.validate(registry.load(root))
    assert any("every seed needs an id" in e for e in errors)
    assert any("duplicate seed ids" in e for e in errors)


def test_agents_load_and_overlay_merges_by_id():
    reg = registry.load(FIX / "repo")
    assert reg.agents["demo-agent"]["global"][0]["path"] == "~/.demo/skills"
    reg = registry.load(FIX / "repo", overlays=[FIX / "overlay"])
    assert reg.agents["demo-agent"]["notes"] == "Overridden by org"
    assert reg.agents["demo-agent"]["name"] == "Demo Agent"


def test_validate_reports_agent_path_without_source(tmp_path):
    import shutil
    root = tmp_path / "r"
    shutil.copytree(FIX / "repo" / "registry", root / "registry")
    (root / "registry/agents/bad.yaml").write_text(
        "id: bad\nname: Bad\ndocs: https://example.org\nglobal: [{path: ~/.bad/skills}]\n"
        "detect: [{path: ~/.bad, source: https://example.org}]\n")
    errors = registry.validate(registry.load(root))
    assert any("agents/bad.yaml" in e and "source" in e for e in errors)


def test_relocation_vars_are_cleared_for_tests():
    from conftest import RELOCATION_VARS
    reg = registry.load()
    used = {r["var"] for a in reg.agents.values() for r in a.get("relocate", [])}
    assert used <= set(RELOCATION_VARS), "add new relocation vars to tests/conftest.py"


def test_validate_checks_the_taxonomy_itself():
    reg = registry.load(FIX / "repo")
    reg.taxonomy = {**reg.taxonomy, "size_keyword_i18n": {"ja": {"small": ["小さい"]}}}  # misspelled block
    assert any("taxonomy" in e and "size_keyword_i18n" in e for e in registry.validate(reg))


def test_canonical_keyword_lists_are_english_and_other_languages_sit_in_locale_blocks():
    reg = registry.load()
    tax = reg.taxonomy
    lists = {f"phase {p['id']}": p["keywords"] for p in tax["phases"]}
    lists |= {f"size {k}": v for k, v in tax["size_keywords"].items()}
    lists |= {f"skill {sid}": s.get("triggers", []) for sid, s in reg.skills.items()}
    stray = {where: [w for w in words if not w.isascii()] for where, words in lists.items()}
    assert not {k: v for k, v in stray.items() if v}, "move non-English words into the <field>_i18n block"
    assert any(p.get("keywords_i18n", {}).get("vi") for p in tax["phases"])  # Vietnamese stays supported
