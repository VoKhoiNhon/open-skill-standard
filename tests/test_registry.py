from pathlib import Path

import pytest
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
    role = yaml.safe_load((root / "registry/roles/data-engineer.yaml").read_text(encoding="utf-8"))
    role["phases"]["build"]["primary"] = ["superpowers/does-not-exist"]
    (root / "registry/roles/data-engineer.yaml").write_text(yaml.safe_dump(role), encoding="utf-8")
    errors = registry.validate(registry.load(root))
    assert any("superpowers/does-not-exist" in e for e in errors)


def test_validate_reports_dangling_alternative_and_schema_error(tmp_path):
    root = tmp_path / "r"
    import shutil
    shutil.copytree(FIX / "repo", root)
    p = root / "registry/adapters/superpowers.yaml"
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    doc["skills"][0]["alternatives"] = ["nobody/missing"]
    doc["skills"][1]["phases"] = ["not-a-phase"]
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")
    errors = registry.validate(registry.load(root))
    assert any("nobody/missing" in e for e in errors)
    assert any("not-a-phase" in e for e in errors)


def test_validate_requires_seed_ids(tmp_path):
    import shutil
    root = tmp_path / "r"
    shutil.copytree(FIX / "repo", root)
    p = root / "registry/roles/data-engineer.yaml"
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    doc["seeds"] = ["no id here", {"id": "a", "text": "x"}, {"id": "a", "text": "y"}]
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")
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
        "detect: [{path: ~/.bad, source: https://example.org}]\n", encoding="utf-8")
    errors = registry.validate(registry.load(root))
    assert any("agents/bad.yaml" in e.replace("\\", "/") and "source" in e for e in errors)


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
    lists["stopwords"] = tax["stopwords"]
    lists |= {f"skill {sid}": s.get("triggers", []) for sid, s in reg.skills.items()}
    stray = {where: [w for w in words if not w.isascii()] for where, words in lists.items()}
    assert not {k: v for k, v in stray.items() if v}, "move non-English words into the <field>_i18n block"
    assert any(p.get("keywords_i18n", {}).get("vi") for p in tax["phases"])  # Vietnamese stays supported


def _shipped_seeds(reg) -> dict[str, str]:
    from open_skill import userdata
    return {f"{rid}/{s['id']}": userdata.text_hash(s["text"]) for rid, r in reg.roles.items() for s in r.get("seeds", [])}


def _renamed(released: dict, current: dict) -> dict[str, str]:
    by_hash = {h: sid for sid, h in current.items()}
    return {old: by_hash[h] for old, hashes in released.items() if old not in current for h in hashes if h in by_hash}


def test_released_seed_ids_are_never_renamed():
    """A released seed id may be retired, never renamed: when an id is gone, no seed may ship one of its wordings."""
    released = yaml.safe_load((FIX / "released-seeds.yaml").read_text(encoding="utf-8"))
    reg = registry.load()
    assert not _renamed(released, _shipped_seeds(reg)), "retire the old id and add a new seed instead (SPEC §5.1)"
    seed = reg.roles["data-engineer"]["seeds"][0]
    old, seed["id"] = seed["id"], "renamed-" + seed["id"]
    assert _renamed(released, _shipped_seeds(reg)) == {f"data-engineer/{old}": f"data-engineer/renamed-{old}"}


def test_seed_texts_are_english():
    texts = [s["text"] for r in registry.load().roles.values() for s in r.get("seeds", [])]
    assert texts and all(t.isascii() for t in texts)


def _set(doc, path, value):
    """Set doc[a][b]... = value along a list of keys and indexes."""
    for k in path[:-1]:
        doc = doc[k]
    doc[path[-1]] = value


def _edit(root, rel, path=None, value=None, raw=None):
    p = root / "registry" / rel
    if raw is not None:
        p.write_text(raw, encoding="utf-8")
        return
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    _set(doc, path, value)
    p.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")


SP = "adapters/superpowers.yaml"
DE = "roles/data-engineer.yaml"
# (case, file, key path, new value, raw file text, expected error text). Every validate check has a row.
VALIDATION_CASES = [
    ("schema error", SP, ["skills", 1, "phases"], ["not-a-phase"], None, "not-a-phase"),
    ("dangling alternative", SP, ["skills", 0, "alternatives"], ["nobody/missing"], None, "alternatives references unknown skill nobody/missing"),
    ("dangling conflict", SP, ["skills", 0, "conflicts"], ["nobody/missing"], None, "conflicts references unknown skill"),
    ("dangling precedes", SP, ["skills", 0, "precedes"], ["nobody/missing"], None, "precedes references unknown skill"),
    ("dangling requires", SP, ["skills", 0, "requires"], ["skill:nobody/missing"], None, "requires unknown skill nobody/missing"),
    ("dangling role primary", DE, ["phases", "build", "primary"], ["superpowers/does-not-exist"], None, "build.primary references unknown skill"),
    ("dangling role alternative", DE, ["phases", "build", "alternatives"], ["x/y"], None, "build.alternatives references unknown skill x/y"),
    ("unknown parent model", "models/claude-opus-5.yaml", ["inherits"], "claude-nope", None, "inherits unknown profile claude-nope"),
    ("seed without id is a string", DE, ["seeds"], ["no id here"], None, "every seed needs an id"),
    ("duplicate seed ids", DE, ["seeds"], [{"id": "a", "text": "x"}, {"id": "a", "text": "y"}], None, "duplicate seed ids: a"),
    # These crashed validate with a traceback instead of reporting an error:
    ("seed object without id", DE, ["seeds"], [{"text": "x"}], None, "seeds/0"),
    ("seeds is null", DE, ["seeds"], None, None, "seeds"),
    ("seed id is a list", DE, ["seeds"], [{"id": ["a"], "text": "x"}], None, "seeds/0"),
    ("adapter skill without name", SP, ["skills", 0], {"phases": ["plan"]}, None, "'name' is a required property"),
    ("adapter skill is a string", SP, ["skills", 0], "brainstorming", None, "is not of type 'object'"),
    ("adapter skills is null", SP, ["skills"], None, None, "skills"),
    # These passed silently:
    ("duplicate skill in one file", SP, ["skills", 1, "name"], "brainstorming", None, "defines skill brainstorming twice"),
    ("model inheritance cycle", "models/generic.yaml", ["inherits"], "claude-opus-5", None, "inheritance cycle"),
    ("detect names an unknown agent", SP, ["detect", 0, "agent"], "no-such-agent", None, "unknown agent no-such-agent"),
    ("handoff to a role without a pack", DE, ["handoff"], {"review": "security-engineer"}, None, "hands off to security-engineer"),
    ("two files, one id", "roles/copy.yaml", None, None, "id: data-engineer\n", "defined in both"),
]


@pytest.mark.parametrize("case,rel,path,value,raw,expected", VALIDATION_CASES, ids=[c[0] for c in VALIDATION_CASES])
def test_validate_reports(tmp_path, case, rel, path, value, raw, expected):
    import shutil
    root = tmp_path / "r"
    shutil.copytree(FIX / "repo", root)
    _edit(root, rel, path, value, raw)
    errors = registry.validate(registry.load(root))
    assert any(expected in e for e in errors), errors
def test_bug_validate_rejects_a_role_entry_outside_the_skills_phases(tmp_path):
    # Eight role pack entries named a skill for a phase it does not act in; the router never considers them there.
    import shutil
    root = tmp_path / "r"
    shutil.copytree(FIX / "repo", root)
    p = root / "registry/roles/data-engineer.yaml"
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    sid = doc["phases"]["build"]["primary"][0]
    skill = registry.load(root).skills[sid]
    wrong = next(ph for ph in ("discover", "research", "release", "learn") if ph not in skill["phases"])
    doc["phases"].setdefault(wrong, {}).setdefault("primary", []).append(sid)
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")
    errors = registry.validate(registry.load(root))
    assert any(f"{wrong}.primary lists {sid}, which acts in" in e for e in errors)
