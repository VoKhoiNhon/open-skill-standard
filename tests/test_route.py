from pathlib import Path

import pytest

from open_skill import knowledge, registry, route
from open_skill.scan import Installed

FIX = Path(__file__).parent / "fixtures"
REG = registry.load(FIX / "repo")


def installed(*ids):
    out = []
    for sid in ids:
        src, name = sid.split("/")
        inv = {"spec-kit": f"speckit-{name}", "superpowers": f"superpowers:{name}",
               "knowledge-work-data": f"data:{name}"}.get(src, name)
        out.append(Installed(sid, inv, "/x", REG.skills.get(sid, {}).get("description", ""), sid not in REG.skills))
    return out


ALL = installed(*REG.skills)


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))


def proj(tmp_path, *files):
    for f in files:
        p = tmp_path / "p" / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    (tmp_path / "p").mkdir(exist_ok=True)
    return tmp_path / "p"


def ids(r):
    return [s["id"] for s in r["chain"]]


def test_native_spec_kit_large_with_spec_starts_at_plan(tmp_path):
    p = proj(tmp_path, ".specify/memory/constitution.md", "specs/001-x/spec.md")
    r = route.route("build a new application for invoices", p, REG, ALL, role="data-engineer")
    assert r["size"] == "large"
    assert r["chain"][0]["phase"] == "plan"
    assert ids(r)[0] == "spec-kit/plan"
    assert "spec-kit/implement" in ids(r)
    assert "superpowers/subagent-driven-development" not in ids(r)


def test_no_native_medium_uses_superpowers_and_one_build_workflow(tmp_path):
    p = proj(tmp_path, "app.py")
    r = route.route("add an export endpoint", p, REG, ALL, role="data-engineer")
    chain = ids(r)
    assert chain[0] == "superpowers/writing-plans"
    assert not ({"spec-kit/implement", "superpowers/subagent-driven-development"} <= set(chain))
    assert all(not s.startswith("spec-kit/") for s in chain)  # needs .specify


def test_data_engineer_verify_and_missing_codegraph(tmp_path):
    p = proj(tmp_path, "dbt_project.yml")
    r = route.route("add a pipeline that loads orders", p, REG, ALL)
    assert "data-engineer" in r["role"]
    assert "knowledge-work-data/validate-data" in ids(r)
    assert any(m["id"] == "codegraph/explore" and m["install"] == "codegraph init" for m in r["missing"])


def test_model_profile_limits_steps_but_keeps_review(tmp_path):
    p = proj(tmp_path, ".specify/x", ".codegraph/db")
    r = route.route("build a new platform", p, REG, ALL, role="data-engineer", model="claude-haiku-4-5")
    assert len(r["chain"]) <= 3
    assert r["chain"][-1]["phase"] == "review"
    assert r["model"]["profile"] == "claude-haiku-4-5"


def test_do_directly_for_trivial_change(tmp_path):
    r = route.route("fix typo in README", proj(tmp_path, "README.md"), REG, ALL)
    assert r["chain"] == [] and r["advice"] == "do directly"


def test_personal_weights_change_ranking(tmp_path):
    p = proj(tmp_path, "app.py")  # no native framework: the choice is left to scores
    base = route.route("write the plan for the feature", p, REG, ALL, role="fullstack-developer", size="medium")
    first = base["chain"][0]["id"]
    other = "superpowers/brainstorming" if first == "superpowers/writing-plans" else "superpowers/writing-plans"
    for i in range(6):
        knowledge.record({"type": "proposed", "route_id": f"x{i}", "chain": [{"id": first, "invoke": "a"}]})
        knowledge.record({"type": "feedback", "route_id": f"x{i}", "ran": ["b"], "outcome": "ok"})
        knowledge.record({"type": "proposed", "route_id": f"y{i}", "chain": [{"id": other, "invoke": "b"}]})
        knowledge.record({"type": "feedback", "route_id": f"y{i}", "ran": ["b"], "outcome": "ok"})
    again = route.route("write the plan for the feature", p, REG, ALL, role="fullstack-developer", size="medium")
    assert again["chain"][0]["id"] == other


def test_knowledge_attached_and_event_recorded(tmp_path):
    knowledge.learn("Backfills duplicated rows with INSERT", ["role:data-engineer"])
    r = route.route("add a pipeline", proj(tmp_path, "x.py"), REG, ALL, role="data-engineer")
    assert any("Backfills" in k["text"] for k in r["knowledge"])
    events = (knowledge.home() / "events.jsonl").read_text()
    assert r["route_id"] in events


def test_harvested_skill_can_be_chosen(tmp_path):
    extra = [Installed("harvested/warehouse-audit", "warehouse-audit", "/x",
                       "Verify and validate warehouse tables for duplicate keys", True)]
    r = route.route("verify duplicate keys in the warehouse tables", proj(tmp_path, "x.py"), REG,
                    installed("superpowers/test-driven-development") + extra, role="data-engineer")
    assert "harvested/warehouse-audit" in ids(r)
    step = next(s for s in r["chain"] if s["id"] == "harvested/warehouse-audit")
    assert "inferred" in step["why"]


def test_role_build_window_replaces_default_chain(tmp_path):
    r = route.route("why did revenue drop last week", proj(tmp_path, "x.sql"), REG, ALL, role="data-analyst")
    assert r["chain"] and {s["phase"] for s in r["chain"]} <= {"build", "verify"}
    assert "knowledge-work-data/validate-data" in ids(r)
    assert "superpowers/writing-plans" not in ids(r)


def test_flow_bonus_prefers_skill_consuming_produced_artifact(tmp_path):
    r = route.route("add an export endpoint", proj(tmp_path, "app.py"), REG, ALL, role="fullstack-developer")
    build = next(s for s in r["chain"] if s["phase"] == "build")
    assert build["id"] == "superpowers/subagent-driven-development"
    assert "consumes plan" in build["why"]


def test_close_calls_only_ask_on_the_target_phase(tmp_path):
    r = route.route("add an export endpoint", proj(tmp_path, "app.py"), REG, ALL, role="fullstack-developer")
    assert all(s["phase"] == r["target_phase"] for s in r["chain"] if "ask" in s)


def test_harvested_skill_needs_more_than_one_shared_word(tmp_path):
    extra = [Installed("harvested/daily-report", "daily-report", "/x",
                       "Analyze numbers and post the daily report to the team channel; specification of the format", True)]
    r = route.route("write a spec for team workspaces", proj(tmp_path, "x.py"), REG, ALL + extra, role="fullstack-developer")
    assert "harvested/daily-report" not in ids(r)


@pytest.mark.parametrize("args,window,reason", [
    (("build", "small", []), ["build"], "small build task: build only"),
    (("build", "medium", [], ["build", "verify"], "data-analyst"), ["build", "verify"], "data-analyst's build_window"),
    (("build", "large", []), ["specify", "plan", "build", "verify", "review"], "large build task: starts at specify"),
    (("build", "large", ["spec"]), ["plan", "build", "verify", "review"], "large build task with a spec in the project"),
    (("build", "medium", ["plan"]), ["build", "verify", "review"], "medium build task with plan in the project"),
    (("build", "large", ["spec", "tasks"]), ["build", "verify", "review"], "with tasks in the project"),
    (("plan", "large", []), ["specify", "plan"], "large plan task without a spec"),
    (("plan", "medium", []), ["plan"], "plan task: plan only"),
    (("operate", "medium", []), ["operate", "build", "verify"], "operate task"),
    (("release", "medium", []), ["verify", "release"], "release task"),
])
def test_window_and_reason(args, window, reason):
    w, why = route.window_and_reason(*args)
    assert w == window and reason in why
    assert route.phase_window(*args[:4]) == window


def test_install_hint_fits_the_agent():
    both = {"source": "demo", "name": "x",
            "install": {"claude-plugin": "/plugin install x@demo", "skills-cli": "npx skills add demo/x -g"}}
    assert route._install_hint(both) == "/plugin install x@demo"
    assert route._install_hint(both, "claude-code") == "/plugin install x@demo"
    assert route._install_hint(both, "codex") == "npx skills add demo/x -g"
    only_plugin = {"source": "demo", "name": "x", "install": {"claude-plugin": "/plugin install x@demo"}}
    assert route._install_hint(only_plugin, "codex") == "/plugin install x@demo"
    init = {"source": "demo", "name": "x", "install": {"skills-cli": "npx skills add demo/x", "project-init": "demo init"}}
    assert route._install_hint(init, "codex") == "demo init"
    core = {"source": "open-skill", "name": "open-skill-router", "install": {"claude-plugin": "/plugin install o"}}
    assert route._install_hint(core, "cursor") == "open-skill install open-skill-router --agent cursor"
    assert route._install_hint(core) == "/plugin install o"


def test_missing_skill_hints_use_the_agent(tmp_path):
    import copy
    reg = copy.deepcopy(REG)
    for s in reg.skills.values():  # every skill also offers a Claude plugin, listed first
        s["install"] = {"claude-plugin": "/plugin install demo", "skills-cli": "npx skills add demo -g"}
    task = "add a pipeline that loads orders"
    have = installed("superpowers/writing-plans")
    claude = route.route(task, proj(tmp_path), reg, have, role="data-engineer", record=False)
    codex = route.route(task, proj(tmp_path), reg, have, role="data-engineer", record=False, agent="codex")
    assert claude["missing"] and {m["install"] for m in claude["missing"]} == {"/plugin install demo"}
    assert codex["agent"] == "codex" and {m["install"] for m in codex["missing"]} == {"npx skills add demo -g"}
