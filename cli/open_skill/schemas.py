"""JSON Schemas for registry documents, derived from the taxonomy so enums never drift."""

KEBAB = "^[a-z0-9]+(-[a-z0-9]+)*$"
SKILL_ID = "^[a-z0-9-]+/[a-z0-9:_-]+$"
URL = "^https://[^\\s]+$"
EFFORT = ["low", "medium", "high", "xhigh", "max"]
LOCALE = "^(?!en(-|$))[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$"  # BCP 47 language tag; English is the canonical list


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


def _i18n(value: dict) -> dict:
    """`<field>_i18n`: locale tag -> what `<field>` holds, in that language (SPEC §3.1)."""
    return {"type": "object", "propertyNames": {"pattern": LOCALE}, "additionalProperties": value,
            "description": "per-locale additions to the English list, keyed by BCP 47 language tag"}


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
            "triggers_i18n": _i18n(_arr({"type": "string"})),
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
            "available_cmd": {"type": "string", "description": "skills count as installed, for every agent, when this command is on PATH"},
            "install": {"type": "object", "additionalProperties": {"type": "string"}},
            "detect": _arr(
                {
                    "type": "object",
                    "required": ["glob", "invoke"],
                    "additionalProperties": False,
                    "properties": {"glob": {"type": "string"}, "invoke": {"type": "string"},
                                   "agent": {"type": "string", "pattern": KEBAB, "description": "agent id, default claude-code"},
                                   "names": _arr({"type": "string"}, minItems=1,
                                                 description="the only skill names this rule claims")},
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
            "seeds": _arr({"oneOf": [
                {"type": "string"},
                {"type": "object", "required": ["id", "text"], "additionalProperties": False,
                 "properties": {"id": {"type": "string", "pattern": KEBAB}, "text": {"type": "string"}}},
            ]}),
            "build_window": _arr({"enum": e["phases"]}, minItems=1),
            "handoff": {"type": "object", "additionalProperties": {"enum": e["roles"]}},
        },
    }


def taxonomy_schema(tax: dict) -> dict:
    e = _enums(tax)
    words = _arr({"type": "string", "minLength": 1})
    sizes = {"type": "object", "propertyNames": {"enum": e["sizes"]}, "additionalProperties": words}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Open Skill Standard taxonomy",
        "type": "object",
        "required": ["version", "phases", "artifacts", "edges", "task_sizes", "role_families", "knowledge_types"],
        "additionalProperties": False,
        "properties": {
            "version": {"type": "string"},
            "phases": _arr({"type": "object", "required": ["id", "keywords"], "additionalProperties": False,
                            "properties": {"id": {"type": "string", "pattern": KEBAB}, "keywords": words,
                                           "keywords_i18n": _i18n(words)}}, minItems=1),
            "artifacts": {"type": "object", "additionalProperties": _arr({"type": "string"})},
            "edges": _arr({"type": "string"}),
            "task_sizes": _arr({"type": "string"}),
            "size_keywords": sizes,
            "size_keywords_i18n": _i18n(sizes),
            "stopwords": words,
            "stopwords_i18n": _i18n(words),
            "role_families": {"type": "object", "additionalProperties": _arr({"type": "string", "pattern": KEBAB})},
            "native_markers": _arr({"type": "object", "required": ["framework", "paths"]}),
            "tool_markers": {"type": "object", "additionalProperties": _arr({"type": "string"})},
            "knowledge_types": _arr({"type": "string"}),
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


def _located(path_pattern: str) -> dict:
    """A path with the URL of the official page (or upstream source line) that documents it."""
    return {
        "type": "object",
        "required": ["path", "source"],
        "additionalProperties": False,
        "properties": {"path": {"type": "string", "pattern": path_pattern}, "source": {"type": "string", "pattern": URL}},
    }


def agent_schema(tax: dict) -> dict:
    absolute = "^(~/|/)"
    relative = "^(?!~|/)(?!.*(^|/)\\.\\.(/|$)).+$"
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Open Skill Standard agent target",
        "type": "object",
        "required": ["id", "name", "docs", "global", "detect"],
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string", "pattern": KEBAB},
            "name": {"type": "string"},
            "docs": {"type": "string", "pattern": URL},
            "global": _arr(_located(absolute), minItems=1, description="user-level skill folders, install target first"),
            "project": _arr(_located(relative), description="skill folders relative to the project root, install target first"),
            "detect": _arr(_located(absolute), minItems=1, description="the agent counts as installed when any path exists"),
            "relocate": _arr({
                "type": "object",
                "required": ["var", "replaces", "source"],
                "additionalProperties": False,
                "properties": {"var": {"type": "string", "pattern": "^[A-Z][A-Z0-9_]*$"},
                               "replaces": {"type": "string", "pattern": absolute},
                               "source": {"type": "string", "pattern": URL}},
            }, description="an env var that, when set, replaces a path prefix"),
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
    "agent": agent_schema,
    "taxonomy": taxonomy_schema,
}


def all_schemas(tax: dict) -> dict[str, dict]:
    return {name: fn(tax) for name, fn in ALL.items()}
