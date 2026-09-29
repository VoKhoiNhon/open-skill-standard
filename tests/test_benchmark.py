import math

import pytest

from open_skill import benchmark, evals, registry, route


@pytest.fixture(scope="module")
def reg():
    return registry.load()


def test_wilson_matches_known_intervals():
    lo, hi = benchmark.wilson(35, 52)
    assert (round(lo, 3), round(hi, 3)) == (0.538, 0.785)
    assert benchmark.wilson(0, 10)[0] < 1e-12 and benchmark.wilson(10, 10)[1] > 1 - 1e-12
    assert benchmark.wilson(0, 0) == (0.0, 1.0)


def test_mcnemar_exact_is_a_two_sided_binomial_test():
    assert benchmark.mcnemar_exact(0, 0) == 1.0
    assert benchmark.mcnemar_exact(5, 5) == 1.0
    assert math.isclose(benchmark.mcnemar_exact(10, 0), 2 / 2 ** 10)
    assert benchmark.mcnemar_exact(3, 29) == benchmark.mcnemar_exact(29, 3)


def test_check_case_reads_a_route_result():
    case = {"first": "a/x", "include": ["a/y"], "phases": ["plan", "build"]}
    ok = {"chain": [{"id": "a/x", "phase": "plan"}, {"id": "a/y", "phase": "build"}], "advice": None}
    assert evals.check_case(case, ok) == []
    assert len(evals.check_case(case, {"chain": [], "advice": None})) == 3


def test_description_match_picks_one_routable_skill(reg):
    conn = benchmark.index.build_index(reg, evals.all_installed(reg))
    r = benchmark.bm25_top1({"task": "the export endpoint is failing with a 500 error"}, reg, conn)
    assert len(r["chain"]) == 1 and r["advice"] is None
    step = r["chain"][0]
    assert reg.skills[step["id"]].get("kind") != "meta"
    assert step["phase"] == reg.skills[step["id"]]["phases"][0]


def test_ablations_restore_the_router():
    fit, target = route.fit, route.target_phase
    with benchmark.ablation("no-phase"):
        assert route.target_phase("the build is failing", {}) == "build"
    with benchmark.ablation("no-role"):
        assert route.fit(0.0, 0.0) == 1.0
    assert (route.fit, route.target_phase) == (fit, target)


def test_router_row_matches_eval_routing(reg):
    rep = benchmark.run(reg, latency=False)
    installed = evals.all_installed(reg)
    for split, name in (("tuned", "routing.yaml"), ("holdout", "routing-holdout.yaml")):
        plain = evals.routing_report(evals.load_routing_cases(name=name), reg, installed)
        assert rep[split]["router"]["passed"] == plain["passed"]
        assert rep[split]["router"]["cases"] == plain["cases"]
    h = rep["holdout"]
    assert h["router"]["rate"] > h["bm25"]["rate"], "the router should beat description match on the holdout"
    assert {k for k, _ in benchmark.SYSTEMS} <= set(h)


def test_benchmark_is_deterministic(reg):
    assert benchmark.run(reg, latency=False) == benchmark.run(reg, latency=False)
