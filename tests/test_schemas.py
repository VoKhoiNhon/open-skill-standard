from pathlib import Path

import jsonschema
import yaml

from open_skill import schemas

TAX = yaml.safe_load((Path(__file__).parents[1] / "spec" / "taxonomy.yaml").read_text())


def test_every_schema_is_valid_draft_2020_12():
    for s in schemas.all_schemas(TAX).values():
        jsonschema.Draft202012Validator.check_schema(s)


def test_minimal_documents_pass():
    adapter = {"source": "demo", "upstream": "https://x", "license": "MIT",
               "skills": [{"name": "tdd", "phases": ["build"], "roles": {"data-engineer": 0.5}}]}
    role = {"id": "data-engineer", "name": "Data Engineer", "family": "data-ai", "summary": "s", "risk": "r",
            "constitution": ["a", "b", "c"], "phases": {"build": {"primary": ["demo/tdd"]}}}
    model = {"id": "generic", "match": ["*"], "source": None, "verified": True}
    jsonschema.validate(adapter, schemas.adapter_schema(TAX))
    jsonschema.validate(role, schemas.role_schema(TAX))
    jsonschema.validate(model, schemas.model_schema(TAX))


def test_unknown_phase_fails():
    bad = {"source": "demo", "upstream": "u", "license": "MIT", "skills": [{"name": "x", "phases": ["deploy-ish"]}]}
    errors = list(jsonschema.Draft202012Validator(schemas.adapter_schema(TAX)).iter_errors(bad))
    assert errors


def test_28_roles_in_five_families():
    roles = [r for fam in TAX["role_families"].values() for r in fam]
    assert len(roles) == len(set(roles)) == 28
    assert len(TAX["role_families"]) == 5


def test_seeds_accept_stable_objects_and_legacy_strings():
    role = {"id": "qa-engineer", "name": "QA", "family": "quality-ops", "summary": "s", "risk": "r",
            "constitution": ["a", "b", "c"], "phases": {},
            "seeds": ["legacy text", {"id": "name-tests-by-behavior", "text": "Name tests after behavior."}]}
    jsonschema.validate(role, schemas.role_schema(TAX))
    role["seeds"] = [{"id": "Bad Id", "text": "x"}]
    assert list(jsonschema.Draft202012Validator(schemas.role_schema(TAX)).iter_errors(role))


def _agent(**kw):
    doc = {"id": "demo-agent", "name": "Demo", "docs": "https://example.org/skills",
           "global": [{"path": "~/.demo/skills", "source": "https://example.org/skills"}],
           "project": [{"path": ".demo/skills", "source": "https://example.org/skills"}],
           "detect": [{"path": "~/.demo", "source": "https://example.org/skills"}]}
    doc.update(kw)
    return doc


def test_agent_target_minimal_passes():
    jsonschema.validate(_agent(), schemas.agent_schema(TAX))


def test_agent_paths_need_a_source_url():
    v = jsonschema.Draft202012Validator(schemas.agent_schema(TAX))
    assert list(v.iter_errors(_agent(**{"global": [{"path": "~/.demo/skills"}]})))
    assert list(v.iter_errors(_agent(**{"global": [{"path": "~/.demo/skills", "source": "my notes"}]})))


def test_agent_global_is_absolute_and_project_is_relative():
    v = jsonschema.Draft202012Validator(schemas.agent_schema(TAX))
    src = "https://example.org/skills"
    assert list(v.iter_errors(_agent(**{"global": [{"path": ".demo/skills", "source": src}]})))
    assert list(v.iter_errors(_agent(project=[{"path": "~/.demo/skills", "source": src}])))
    assert list(v.iter_errors(_agent(project=[{"path": "../outside/skills", "source": src}])))
    assert list(v.iter_errors(_agent(project=[{"path": "/etc/skills", "source": src}])))


def test_agent_relocation_names_an_env_var_and_prefix():
    v = jsonschema.Draft202012Validator(schemas.agent_schema(TAX))
    ok = [{"var": "DEMO_HOME", "replaces": "~/.demo", "source": "https://example.org/env"}]
    assert not list(v.iter_errors(_agent(relocate=ok)))
    assert list(v.iter_errors(_agent(relocate=[{"var": "demo home", "replaces": "~/.demo", "source": "https://x.org"}])))


def test_locale_blocks_take_a_locale_tag_other_than_english():
    v = jsonschema.Draft202012Validator(schemas.adapter_schema(TAX))
    doc = {"source": "demo", "upstream": "u", "license": "MIT", "skills": [{"name": "x", "phases": ["build"]}]}
    for tag in ("vi", "ja", "es", "pt-BR", "zh-Hant"):
        doc["skills"][0]["triggers_i18n"] = {tag: ["word"]}
        assert not list(v.iter_errors(doc)), tag
    for tag in ("en", "en-GB", "EN", "vietnamese", "vi_VN"):  # English is the canonical list, not a locale block
        doc["skills"][0]["triggers_i18n"] = {tag: ["word"]}
        assert list(v.iter_errors(doc)), tag
    doc["skills"][0]["triggers_i18n"] = {"vi": "not a list"}
    assert list(v.iter_errors(doc))


def test_taxonomy_matches_its_schema_and_rejects_misspelled_locale_blocks():
    v = jsonschema.Draft202012Validator(schemas.taxonomy_schema(TAX))
    assert not list(v.iter_errors(TAX))
    import copy
    bad = copy.deepcopy(TAX)
    bad["phases"][0]["keyword_i18n"] = {"ja": ["アイデア"]}
    assert list(v.iter_errors(bad))
    bad = copy.deepcopy(TAX)
    bad["size_keywords_i18n"] = {"ja": {"huge": ["巨大"]}}
    assert list(v.iter_errors(bad))
