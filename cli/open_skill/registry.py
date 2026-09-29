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


def _yaml_files(d: Path):
    return sorted(p for p in d.glob("*.y*ml") if p.suffix in (".yaml", ".yml")) if d.is_dir() else []


def _read(p: Path) -> dict:
    doc = yaml.safe_load(p.read_text()) or {}
    if not isinstance(doc, dict):
        raise ValueError(f"{p}: top level must be a mapping")
    return doc


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
        for p in _yaml_files(layer / "adapters"):
            doc = _read(p)
            src = doc.get("source", p.stem)
            base = reg.adapters.setdefault(src, {"source": src, "skills": []})
            by_name = {s["name"]: s for s in base.get("skills", [])}
            for s in doc.get("skills", []):
                by_name.setdefault(s["name"], {}).update(s)
            base.update({k: v for k, v in doc.items() if k != "skills"})
            base["skills"] = list(by_name.values())
            reg.files[f"adapter:{src}"] = str(p)
        for p in _yaml_files(layer / "roles"):
            doc = _read(p)
            rid = doc.get("id", p.stem)
            reg.roles.setdefault(rid, {}).update(doc)
            reg.files[f"role:{rid}"] = str(p)
        for p in _yaml_files(layer / "models"):
            doc = _read(p)
            mid = doc.get("id", p.stem)
            reg.models.setdefault(mid, {}).update(doc)
            reg.files[f"model:{mid}"] = str(p)
        for p in _yaml_files(layer / "agents"):
            doc = _read(p)
            aid = doc.get("id", p.stem)
            reg.agents.setdefault(aid, {}).update(doc)
            reg.files[f"agent:{aid}"] = str(p)
    for src, a in reg.adapters.items():
        for s in a.get("skills", []):
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
    errors: list[str] = []
    for src, a in reg.adapters.items():
        errors += _schema_errors(a, sch["adapter"], reg.files.get(f"adapter:{src}", src))
    for rid, r in reg.roles.items():
        errors += _schema_errors(r, sch["role"], reg.files.get(f"role:{rid}", rid))
    for mid, m in reg.models.items():
        errors += _schema_errors(m, sch["model"], reg.files.get(f"model:{mid}", mid))
    for aid, a in reg.agents.items():
        errors += _schema_errors(a, sch["agent"], reg.files.get(f"agent:{aid}", aid))

    known = set(reg.skills)
    for sid, s in reg.skills.items():
        for key in ("alternatives", "conflicts", "precedes"):
            for ref in s.get(key, []):
                if ref not in known:
                    errors.append(f"skill {sid}: {key} references unknown skill {ref}")
        for req in s.get("requires", []):
            if req.startswith("skill:") and req[6:] not in known:
                errors.append(f"skill {sid}: requires unknown skill {req[6:]}")
    for rid, r in reg.roles.items():
        for phase, entry in (r.get("phases") or {}).items():
            for key in ("primary", "alternatives"):
                for ref in (entry or {}).get(key, []):
                    if ref not in known:
                        errors.append(f"role {rid}: {phase}.{key} references unknown skill {ref}")
    for rid, r in reg.roles.items():
        ids = [s["id"] for s in r.get("seeds", []) if isinstance(s, dict)]
        if any(isinstance(s, str) for s in r.get("seeds", [])):
            errors.append(f"role {rid}: every seed needs an id so it can be updated without touching user edits")
        if len(ids) != len(set(ids)):
            errors.append(f"role {rid}: duplicate seed ids")
    for mid, m in reg.models.items():
        parent = m.get("inherits")
        if parent and parent not in reg.models:
            errors.append(f"model {mid}: inherits unknown profile {parent}")
    return errors
