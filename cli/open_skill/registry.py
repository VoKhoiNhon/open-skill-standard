"""Load and validate the YAML registry (adapters, role packs, model profiles, agent targets)."""

from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
import yaml

from . import paths, schemas

INHERITED = ("install", "portability", "upstream", "license", "trademark_note")


@dataclass
class Registry:
    taxonomy: dict
    adapters: dict[str, dict] = field(default_factory=dict)
    skills: dict[str, dict] = field(default_factory=dict)
    roles: dict[str, dict] = field(default_factory=dict)
    models: dict[str, dict] = field(default_factory=dict)
    agents: dict[str, dict] = field(default_factory=dict)  # coding agents and the folders they load skills from
    files: dict[str, str] = field(default_factory=dict)  # "<kind>:<id>" -> file path, for error messages
    problems: list[str] = field(default_factory=list)  # found while loading; validate reports them


def _list(v) -> list:
    """A YAML list field, or [] when it is missing or not a list (the schema reports the wrong type)."""
    return v if isinstance(v, list) else []


def _named(s) -> bool:
    return isinstance(s, dict) and isinstance(s.get("name"), str)


def _yaml_files(d: Path):
    return sorted(p for p in d.glob("*.y*ml") if p.suffix in (".yaml", ".yml")) if d.is_dir() else []


def _read(p: Path) -> dict:
    try:
        doc = yaml.safe_load(p.read_text()) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"{p}: not valid YAML: {e}") from e
    if not isinstance(doc, dict):
        raise ValueError(f"{p}: top level must be a mapping")
    return doc


def localized(doc: dict, key: str):
    """`doc[key]`, the English list, plus every locale block under `doc[key + "_i18n"]` (SPEC §3.1). For a mapping
    of lists such as size_keywords, each list gets the same entry of every block."""
    base, blocks = doc.get(key), list((doc.get(f"{key}_i18n") or {}).values())
    if isinstance(base, dict):
        return {k: list(v) + [w for b in blocks for w in b.get(k, [])] for k, v in base.items()}
    return list(base or []) + [w for b in blocks for w in b]


def load_taxonomy(root: Path | None = None) -> dict:
    for base in (root, paths.data_root()):
        if base and (base / "spec" / "taxonomy.yaml").is_file():
            return yaml.safe_load((base / "spec" / "taxonomy.yaml").read_text())
    raise FileNotFoundError("spec/taxonomy.yaml not found")


def load(root: Path | None = None, overlays=()) -> Registry:
    """Load <root>/registry, then each overlay dir (same layout, later wins)."""
    root = Path(root) if root else paths.data_root()
    reg = Registry(taxonomy=load_taxonomy(root))
    for layer in [root / "registry", *map(Path, overlays)]:
        seen: dict[str, Path] = {}

        def claim(key: str, p: Path) -> None:
            """Overlays override by id on purpose; two files of one layer with one id are a mistake."""
            if key in seen:
                reg.problems.append(f"{key.replace(':', ' ', 1)} is defined in both {seen[key]} and {p}")
            seen[key] = p
            reg.files[key] = str(p)

        for p in _yaml_files(layer / "adapters"):
            doc = _read(p)
            src = doc.get("source", p.stem)
            base = reg.adapters.setdefault(src, {"source": src, "skills": []})
            by_name = {s["name"]: s for s in base.get("skills", []) if _named(s)}
            broken = [s for s in base.get("skills", []) if not _named(s)]
            names = [s["name"] for s in _list(doc.get("skills")) if _named(s)]
            for n in sorted({n for n in names if names.count(n) > 1}):  # overlays merge by name; one file must not
                reg.problems.append(f"{p}: defines skill {n} twice; the entries would be merged silently")
            for s in _list(doc.get("skills")):
                if _named(s):
                    by_name.setdefault(s["name"], {}).update(s)
                else:  # kept as is, so the schema check reports it instead of load crashing on it
                    broken.append(s)
            base.update({k: v for k, v in doc.items() if k != "skills"})
            base["skills"] = list(by_name.values()) + broken
            claim(f"adapter:{src}", p)
        for p in _yaml_files(layer / "roles"):
            doc = _read(p)
            rid = doc.get("id", p.stem)
            reg.roles.setdefault(rid, {}).update(doc)
            claim(f"role:{rid}", p)
        for p in _yaml_files(layer / "models"):
            doc = _read(p)
            mid = doc.get("id", p.stem)
            reg.models.setdefault(mid, {}).update(doc)
            claim(f"model:{mid}", p)
        for p in _yaml_files(layer / "agents"):
            doc = _read(p)
            aid = doc.get("id", p.stem)
            reg.agents.setdefault(aid, {}).update(doc)
            claim(f"agent:{aid}", p)
    for src, a in reg.adapters.items():
        for s in filter(_named, a.get("skills", [])):
            m = {k: a[k] for k in INHERITED if k in a}
            m.update(s)
            m["source"] = src
            m.setdefault("kind", "skill")
            reg.skills[f"{src}/{s['name']}"] = m
    return reg


def _schema_errors(doc: dict, schema: dict, where: str) -> list[str]:
    out = []
    for e in jsonschema.Draft202012Validator(schema).iter_errors(doc):
        loc = "/".join(str(x) for x in e.absolute_path)
        out.append(f"{where}: {loc or '<root>'}: {e.message}")
    return out


def validate(reg: Registry) -> list[str]:
    """Schema checks per document plus cross-reference checks. Empty list means valid."""
    sch = schemas.all_schemas(reg.taxonomy)
    errors: list[str] = reg.problems + _schema_errors(reg.taxonomy, sch["taxonomy"], "spec/taxonomy.yaml")
    for src, a in reg.adapters.items():
        errors += _schema_errors(a, sch["adapter"], reg.files.get(f"adapter:{src}", src))
    for rid, r in reg.roles.items():
        errors += _schema_errors(r, sch["role"], reg.files.get(f"role:{rid}", rid))
    for mid, m in reg.models.items():
        errors += _schema_errors(m, sch["model"], reg.files.get(f"model:{mid}", mid))
    for aid, a in reg.agents.items():
        errors += _schema_errors(a, sch["agent"], reg.files.get(f"agent:{aid}", aid))

    known = set(reg.skills)
    for src, a in reg.adapters.items():
        for rule in _list(a.get("detect")):
            agent = rule.get("agent") if isinstance(rule, dict) else None
            if agent and agent not in reg.agents:  # the rule would then describe folders no agent reads
                errors.append(f"adapter {src}: detect rule {rule.get('glob')} names unknown agent {agent}")
    for sid, s in reg.skills.items():
        for key in ("alternatives", "conflicts", "precedes"):
            for ref in _list(s.get(key)):
                if ref not in known:
                    errors.append(f"skill {sid}: {key} references unknown skill {ref}")
        for req in _list(s.get("requires")):
            if isinstance(req, str) and req.startswith("skill:") and req[6:] not in known:
                errors.append(f"skill {sid}: requires unknown skill {req[6:]}")
    for rid, r in reg.roles.items():
        phases = r.get("phases") if isinstance(r.get("phases"), dict) else {}
        for phase, entry in phases.items():
            for key in ("primary", "alternatives"):
                for ref in _list((entry if isinstance(entry, dict) else {}).get(key)):
                    if ref not in known:
                        errors.append(f"role {rid}: {phase}.{key} references unknown skill {ref}")
    for rid, r in reg.roles.items():
        handoff = r.get("handoff") if isinstance(r.get("handoff"), dict) else {}
        for when, target in handoff.items():  # the schema allows any taxonomy role; the playbook links to its pack
            if target not in reg.roles:
                errors.append(f"role {rid}: {when} hands off to {target}, which has no role pack")
        seeds = _list(r.get("seeds"))
        ids = [s["id"] for s in seeds if isinstance(s, dict) and isinstance(s.get("id"), str)]
        if any(isinstance(s, str) for s in seeds):
            errors.append(f"role {rid}: every seed needs an id so it can be updated without touching user edits")
        if len(ids) != len(set(ids)):
            errors.append(f"role {rid}: duplicate seed ids: {', '.join(sorted({i for i in ids if ids.count(i) > 1}))}")
    for mid, m in reg.models.items():
        parent = m.get("inherits")
        if parent and parent not in reg.models:
            errors.append(f"model {mid}: inherits unknown profile {parent}")
        chain = [mid]
        while (parent := reg.models.get(chain[-1], {}).get("inherits")) and parent in reg.models:
            if parent in chain:  # resolving any model in the loop would raise, so every route would fail
                errors.append(f"model {mid}: inheritance cycle {' -> '.join(chain + [parent])}")
                break
            chain.append(parent)
    return errors
