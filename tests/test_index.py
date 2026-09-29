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


def test_graph_json_describes_skills_and_roles():
    reg, inst = setup()
    nodes = {n["id"]: n for n in index.graph_json(reg, inst)["nodes"]}
    assert nodes["superpowers/writing-plans"]["description"].startswith("Write a detailed implementation plan")
    assert nodes["harvested/warehouse-audit"]["description"] == "Audit warehouse tables for duplicate keys"
    assert nodes["role:data-analyst"]["name"] == "Data Analyst"


def test_skill_filters_by_role_phase_and_source():
    reg, inst = setup()
    ids = list(reg.skills) + ["harvested/warehouse-audit"]
    keep = lambda **kw: {s for s in ids if index.matches(reg, s, **kw)}  # noqa: E731
    assert keep(phase="verify") == {"knowledge-work-data/validate-data", "superpowers/test-driven-development"}
    assert keep(source="spec-kit") == {"spec-kit/specify", "spec-kit/plan", "spec-kit/implement"}
    assert keep(source="harvested") == {"harvested/warehouse-audit"}
    # a role keeps skills its role pack lists (primary or alternative) and skills whose manifest names the role
    analyst = keep(role="data-analyst")
    assert analyst == {"knowledge-work-data/validate-data"}
    assert "spec-kit/plan" in keep(role="data-engineer") and "superpowers/brainstorming" not in keep(role="data-engineer")
    assert keep(role="data-engineer", phase="plan", source="superpowers") == {"superpowers/writing-plans"}
    assert keep() == set(ids)


def test_fold_tokenizes_like_the_index():
    assert index.fold("Xuất hóa-đơn ra CSV, đang bị LỖI!") == "xuat hoa don ra csv dang bi loi"
    assert index.fold("pressure-test") == index.fold("pressure test") == "pressure test"


def test_search_folds_d_with_stroke():
    reg, _ = setup()
    conn = index.build_index(reg, [Installed("harvested/x", "x", "/x", "xuất đơn hàng", True)])
    assert [sid for sid, _ in index.search(conn, "don")] == ["harvested/x"]
    assert [sid for sid, _ in index.search(conn, "đơn")] == ["harvested/x"]
