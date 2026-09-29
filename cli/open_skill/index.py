"""SQLite FTS5 search index and graph exports."""

import re
import sqlite3

TOKEN = re.compile(r"\w{2,}", re.UNICODE)
STOP = set("""a an the to of in on for and or not is it this that these those with be are was as at by from into
my our your we i you me us please can could should would will how what why when where which who do does did
make get use using need want just also some any all new one
và của cho là có các những một này đó với được trong không thì mà để khi như nào gì bị""".split())


def _doc(sid: str, s: dict) -> str:
    parts = [sid.replace("/", " ").replace("-", " "), s.get("description", "")]
    parts += s.get("triggers", [])
    parts += [p for p in s.get("phases", [])]
    parts += [r.replace("-", " ") for r in s.get("roles", {})]
    return " ".join(parts)


def build_index(reg, installed=(), path: str = ":memory:") -> sqlite3.Connection:
    """FTS5 index over registry skills plus installed skills without a manifest (in memory by default)."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE VIRTUAL TABLE skills USING fts5(id UNINDEXED, text, tokenize='unicode61 remove_diacritics 2')")
    rows = [(sid, _doc(sid, s)) for sid, s in reg.skills.items()]
    rows += [(i.id, f"{i.invoke.replace('-', ' ')} {i.description}") for i in installed if i.id not in reg.skills]
    conn.executemany("INSERT INTO skills VALUES (?, ?)", rows)
    conn.commit()
    return conn


def search(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[tuple[str, float]]:
    """(skill id, relevance > 0), best first. Every token is quoted, so user text can't break FTS syntax."""
    tokens = [t for t in TOKEN.findall(query.lower()) if t not in STOP and t != "near"]
    if not tokens:
        return []
    q = " OR ".join(f'"{t}"' for t in dict.fromkeys(tokens))
    rows = conn.execute(
        "SELECT id, bm25(skills) FROM skills WHERE skills MATCH ? ORDER BY bm25(skills) LIMIT ?", (q, limit)
    ).fetchall()
    return [(sid, -score + 1e-9) for sid, score in rows]  # bm25 is lower-is-better and negative


def matches(reg, sid: str, role: str | None = None, phase: str | None = None, source: str | None = None) -> bool:
    """Filter used by search: the role pack lists the skill or its manifest names the role; phase; source."""
    s = reg.skills.get(sid) or {}
    if source and sid.split("/")[0] != source:
        return False
    if phase and phase not in s.get("phases", []):
        return False
    if role:
        pack = (reg.roles.get(role) or {}).get("phases") or {}
        listed = any(sid in (e or {}).get(k, []) for e in pack.values() for k in ("primary", "alternatives"))
        if not listed and role not in (s.get("roles") or {}):
            return False
    return True


def graph_json(reg, installed=()) -> dict:
    inst = {i.id for i in installed}
    nodes, edges = [], []
    for p in reg.taxonomy["phases"]:
        nodes.append({"id": f"phase:{p['id']}", "kind": "phase"})
    for a in reg.taxonomy["artifacts"]:
        nodes.append({"id": f"artifact:{a}", "kind": "artifact"})
    for sid, s in sorted(reg.skills.items()):
        nodes.append({"id": sid, "kind": s.get("kind", "skill"), "source": s["source"],
                      "phases": s.get("phases", []), "installed": sid in inst, "description": s.get("description", "")})
        for a in s.get("produces", []):
            edges.append({"from": sid, "to": f"artifact:{a}", "type": "produces"})
        for a in s.get("consumes", []):
            edges.append({"from": f"artifact:{a}", "to": sid, "type": "consumes"})
        for key, etype in (("alternatives", "alternative-to"), ("conflicts", "conflicts-with"), ("precedes", "precedes")):
            for ref in s.get(key, []):
                edges.append({"from": sid, "to": ref, "type": etype})
        for req in s.get("requires", []):
            edges.append({"from": sid, "to": req, "type": "requires"})
    for i in installed:
        if i.id not in reg.skills:
            nodes.append({"id": i.id, "kind": "skill", "source": i.id.split("/")[0], "phases": [],
                          "installed": True, "inferred": True, "description": i.description})
    for rid, r in sorted(reg.roles.items()):
        nodes.append({"id": f"role:{rid}", "kind": "role", "name": r.get("name", rid), "family": r.get("family")})
        seen = set()
        for entry in (r.get("phases") or {}).values():
            for ref in entry.get("primary", []):
                if ref not in seen:
                    seen.add(ref)
                    edges.append({"from": f"role:{rid}", "to": ref, "type": "recommends"})
    return {"version": reg.taxonomy.get("version"), "nodes": nodes, "edges": edges}


def _mid(x: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", x)


def graph_mermaid(reg) -> str:
    """Skills grouped by their first phase, with produces edges to artifacts."""
    lines = ["graph LR"]
    phases = [p["id"] for p in reg.taxonomy["phases"]]
    for ph in phases:
        members = [sid for sid, s in sorted(reg.skills.items()) if (s.get("phases") or [None])[0] == ph]
        if not members:
            continue
        lines.append(f"  subgraph {ph}")
        lines += [f'    {_mid(sid)}["{sid}"]' for sid in members]
        lines.append("  end")
    for sid, s in sorted(reg.skills.items()):
        for a in s.get("produces", []):
            lines.append(f"  {_mid(sid)} --> {_mid('artifact_' + a)}(({a}))")
    return "\n".join(lines) + "\n"
