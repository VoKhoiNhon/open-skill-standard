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
