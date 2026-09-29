from pathlib import Path

from open_skill import index, registry
from open_skill.scan import Installed

FIX = Path(__file__).parent / "fixtures"


def setup():
    reg = registry.load(FIX / "repo")
    inst = [Installed("harvested/warehouse-audit", "warehouse-audit", "/x", "Audit warehouse tables for duplicate keys", True)]
    return reg, inst


def test_search_ranks_triggers():
    reg, inst = setup()
    conn = index.build_index(reg, inst)
    hits = index.search(conn, "write the test first please")
    assert hits[0][0] == "superpowers/test-driven-development"
    assert all(score > 0 for _, score in hits)


def test_search_covers_harvested_and_survives_fts_syntax():
    reg, inst = setup()
    conn = index.build_index(reg, inst)
    assert index.search(conn, "duplicate keys in warehouse")[0][0] == "harvested/warehouse-audit"
    assert index.search(conn, 'AND OR "(* NEAR') == []


def test_vietnamese_diacritics_fold():
    reg, inst = setup()
    conn = index.build_index(reg, [Installed("harvested/x", "x", "/x", "kiểm tra đối soát dữ liệu", True)])
    assert index.search(conn, "doi soat du lieu")[0][0] == "harvested/x"


def test_graph_json_and_mermaid():
    reg, inst = setup()
    g = index.graph_json(reg, inst)
    kinds = {n["kind"] for n in g["nodes"]}
    assert {"skill", "role", "artifact", "phase"} <= kinds
    assert {"from": "superpowers/writing-plans", "to": "artifact:plan", "type": "produces"} in g["edges"]
    assert {"from": "role:data-engineer", "to": "superpowers/writing-plans", "type": "recommends"} in g["edges"]
    installed = {n["id"]: n.get("installed") for n in g["nodes"] if n["kind"] == "skill"}
    assert installed["harvested/warehouse-audit"] is True
    assert index.graph_mermaid(reg).startswith("graph LR")
