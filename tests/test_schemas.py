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
