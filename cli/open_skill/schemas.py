"""JSON Schemas for registry documents, derived from the taxonomy so enums never drift."""

KEBAB = "^[a-z0-9]+(-[a-z0-9]+)*$"
SKILL_ID = "^[a-z0-9-]+/[a-z0-9:_-]+$"
EFFORT = ["low", "medium", "high", "xhigh", "max"]


def _enums(tax: dict) -> dict:
    return {
        "phases": [p["id"] for p in tax["phases"]],
        "artifacts": list(tax["artifacts"]),
        "roles": [r for fam in tax["role_families"].values() for r in fam],
        "families": list(tax["role_families"]),
        "sizes": list(tax["task_sizes"]),
        "ktypes": list(tax["knowledge_types"]),
    }


def _arr(items: dict, **kw) -> dict:
    return {"type": "array", "items": items, **kw}


def adapter_schema(tax: dict) -> dict:
    e = _enums(tax)
    ids = _arr({"type": "string", "pattern": SKILL_ID})
    skill = {
        "type": "object",
        "required": ["name", "phases"],
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "pattern": "^[a-z0-9][a-z0-9:_-]*$"},
            "kind": {"enum": ["skill", "tool"]},
            "description": {"type": "string"},
            "roles": {
                "type": "object",
                "propertyNames": {"enum": e["roles"]},
                "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "phases": _arr({"enum": e["phases"]}, minItems=1),
            "produces": _arr({"enum": e["artifacts"]}),
            "consumes": _arr({"enum": e["artifacts"]}),
            "alternatives": ids,
            "conflicts": ids,
            "precedes": ids,
            "requires": _arr({"type": "string", "pattern": "^(tool|skill|project):.+$"}),
            "task_size": _arr({"enum": e["sizes"]}),
            "triggers": _arr({"type": "string"}),
            "portability": _arr({"type": "string"}),
            "invoke": {"type": "string"},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Open Skill Standard adapter",
        "type": "object",
        "required": ["source", "upstream", "license", "skills"],
        "additionalProperties": False,
        "properties": {
            "source": {"type": "string", "pattern": KEBAB},
            "upstream": {"type": "string"},
            "license": {"type": "string"},
            "trademark_note": {"type": ["string", "null"]},
            "tested_version": {"type": ["string", "null"]},
            "summary": {"type": "string"},
            "available_env": {"type": "string", "description": "skills count as installed when this env var is set"},
            "install": {"type": "object", "additionalProperties": {"type": "string"}},
            "detect": _arr(
                {
                    "type": "object",
                    "required": ["glob", "invoke"],
                    "additionalProperties": False,
                    "properties": {"glob": {"type": "string"}, "invoke": {"type": "string"}},
                }
            ),
            "portability": _arr({"type": "string"}),
            "skills": _arr(skill, minItems=1),
        },
    }


def role_schema(tax: dict) -> dict:
    e = _enums(tax)
    ids = _arr({"type": "string", "pattern": SKILL_ID})
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Open Skill Standard role pack",
        "type": "object",
        "required": ["id", "name", "family", "summary", "risk", "constitution", "phases"],
        "additionalProperties": False,
        "properties": {
            "id": {"enum": e["roles"]},
            "name": {"type": "string"},
            "family": {"enum": e["families"]},
            "summary": {"type": "string"},
            "risk": {"type": "string"},
            "constitution": _arr({"type": "string"}, minItems=3),
            "signals": _arr({"type": "string"}),
            "phases": {
                "type": "object",
                "propertyNames": {"enum": e["phases"]},
                "additionalProperties": {
                    "type": "object",
                    "required": ["primary"],
                    "additionalProperties": False,
                    "properties": {"primary": ids, "alternatives": ids, "note": {"type": "string"}},
                },
            },
            "seeds": _arr({"type": "string"}),
            "build_window": _arr({"enum": e["phases"]}, minItems=1),
            "handoff": {"type": "object", "additionalProperties": {"enum": e["roles"]}},
        },
    }


def model_schema(tax: dict) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Open Skill Standard model profile",
        "type": "object",
        "required": ["id", "match", "source", "verified"],
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string", "pattern": KEBAB},
            "match": _arr({"type": "string"}),
            "family": {"type": ["string", "null"]},
            "inherits": {"type": ["string", "null"]},
            "source": {"type": ["string", "null"]},
            "verified": {"type": ["string", "boolean"]},
            "traits": {"type": "object", "additionalProperties": {"type": ["boolean", "string"]}},
            "effort": {
                "type": "object",
                "propertyNames": {"enum": list(tax["task_sizes"])},
                "additionalProperties": {"enum": EFFORT},
            },
            "chain": {"type": "object", "properties": {"max_steps": {"type": "integer", "minimum": 1}}},
            "addenda": _arr({"type": "string"}),
            "avoid": _arr({"type": "string"}),
            "notes": {"type": "string"},
        },
    }


def knowledge_schema(tax: dict) -> dict:
    e = _enums(tax)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Open Skill Standard knowledge node",
        "type": "object",
        "required": ["id", "type", "applies_to", "source", "created"],
        "properties": {
            "id": {"type": "string"},
            "kind": {"const": "knowledge"},
            "type": {"enum": e["ktypes"]},
            "applies_to": _arr({"type": "string", "pattern": "^(skill|role|project|phase):.+$"}),
            "source": {"enum": ["user", "seed", "agent-memory", "org"]},
            "created": {"type": "string"},
            "summary": {"type": "string"},
        },
    }


ALL = {
    "adapter": adapter_schema,
    "role": role_schema,
    "model": model_schema,
    "knowledge": knowledge_schema,
}


def all_schemas(tax: dict) -> dict[str, dict]:
    return {name: fn(tax) for name, fn in ALL.items()}
