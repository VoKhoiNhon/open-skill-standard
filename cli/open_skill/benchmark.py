"""Routing benchmark: the router against baselines and ablations on the labeled routing cases.

Every system is scored with the same checks (evals.check_case), on the tuned cases and on the held-out cases the
router was never tuned on. Deterministic except for latency: the random baseline uses a fixed seed.

    uv run python -m open_skill.benchmark            # table on stdout
    uv run python -m open_skill.benchmark --json     # the same numbers as JSON
"""

import argparse
import json
import math
import platform
import random
import statistics
import sys
import time
from contextlib import contextmanager

from . import evals, index, registry, route

SEED = 20260929
RANDOM_DRAWS = 200
Z95 = 1.959964


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, mid - half), min(1.0, mid + half)


def mcnemar_exact(wins: int, losses: int) -> float:
    """Two-sided exact McNemar test: a binomial test on the discordant pairs."""
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(wins, losses) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def _eligible(reg) -> dict[str, list[str]]:
    """phase -> routable registry skills in that phase (meta skills never route)."""
    out = {}
    for sid, s in sorted(reg.skills.items()):
        if s.get("kind") == "meta":
            continue
        for p in s.get("phases", []):
            out.setdefault(p, []).append(sid)
    return out


def bm25_top1(case: dict, reg, conn) -> dict:
    """Description match only: the one skill whose name and description best match the task, by BM25 over the
    router's own full-text index (same tokenizer and accent folding), as an agent choosing from descriptions alone
    would. It gets the first phase its manifest lists."""
    top = next((sid for sid, _ in index.search(conn, case["task"], limit=50)
                if reg.skills.get(sid, {}).get("kind") != "meta"), None)
    chain = [{"id": top, "phase": (reg.skills[top].get("phases") or ["build"])[0]}] if top else []
    return {"chain": chain, "advice": None}


def random_in_phases(case: dict, routed: dict, eligible: dict, rng: random.Random) -> float:
    """Expected pass rate when every step of the router's chain is replaced by a random skill of the same phase:
    the router's phases, without its skill choice."""
    if not routed["chain"]:
        return float(not evals.check_case(case, routed))
    passed = 0
    for _ in range(RANDOM_DRAWS):
        chain = [{"id": rng.choice(eligible.get(s["phase"]) or [s["id"]]), "phase": s["phase"]} for s in routed["chain"]]
        passed += not evals.check_case(case, {"chain": chain, "advice": routed["advice"]})
    return passed / RANDOM_DRAWS


@contextmanager
def _patched(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


@contextmanager
def ablation(kind: str | None):
    """no-phase: every task targets build (no phase detection). no-role: every skill gets the same role prior."""
    if kind == "no-phase":
        with _patched(route, "target_phase", lambda task, tax: "build"):
            yield
    elif kind == "no-role":
        with _patched(route, "fit", lambda prior, s: max(route._text(s), s / route.TEXT_ALONE)):
            yield
    else:
        yield


SYSTEMS = [
    ("bm25", "Description match only (BM25, top-1)"),
    ("random", "Random skill in the router's phases"),
    ("no-phase", "Router without phase detection"),
    ("no-role", "Router without role priors"),
    ("router", "Open Skill router"),
]


def score(cases: list[dict], reg, installed) -> dict:
    """Per system: passes per case (floats for the random baseline's expected pass)."""
    rng = random.Random(SEED)
    eligible = _eligible(reg)
    conn = index.build_index(reg, installed)
    out = {"router": [], "bm25": [], "random": []}
    for case in cases:
        r = evals.route_case(case, reg, installed)
        out["router"].append(float(not evals.check_case(case, r)))
        out["bm25"].append(float(not evals.check_case(case, bm25_top1(case, reg, conn))))
        out["random"].append(random_in_phases(case, r, eligible, rng))
    for kind in ("no-phase", "no-role"):
        with ablation(kind):
            out[kind] = [float(not evals.run_case(c, reg, installed)) for c in cases]
    return out


def summarize(passes: dict, n: int) -> dict:
    rows = {}
    for key, label in SYSTEMS:
        k = sum(passes[key])
        lo, hi = wilson(round(k), n)
        rows[key] = {"label": label, "passed": round(k, 2), "cases": n, "rate": round(k / n, 3) if n else 0.0,
                     "ci95": [round(lo, 3), round(hi, 3)]}
    wins = sum(1 for a, b in zip(passes["router"], passes["bm25"]) if a and not b)
    losses = sum(1 for a, b in zip(passes["router"], passes["bm25"]) if b and not a)
    rows["router"]["vs_bm25"] = {"wins": wins, "losses": losses, "mcnemar_p": mcnemar_exact(wins, losses)}
    return rows


def latency_ms(cases: list[dict], reg, installed, repeat: int = 3) -> dict:
    times = []
    for _ in range(repeat):
        for c in cases:
            t = time.perf_counter()
            evals.route_case(c, reg, installed)
            times.append((time.perf_counter() - t) * 1000)
    q = statistics.quantiles(times, n=20)
    return {"median": round(statistics.median(times), 2), "p95": round(q[18], 2), "routes": len(times),
            "machine": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}"}


def run(reg=None, latency: bool = True) -> dict:
    reg = reg or registry.load()
    installed = evals.all_installed(reg)
    out = {}
    for split, name in (("tuned", "routing.yaml"), ("holdout", "routing-holdout.yaml")):
        cases = evals.load_routing_cases(name=name)
        out[split] = summarize(score(cases, reg, installed), len(cases))
    if latency:
        out["latency_ms"] = latency_ms(evals.load_routing_cases(name="routing-holdout.yaml"), reg, installed)
    return out


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-latency", action="store_true")
    args = ap.parse_args(argv)
    rep = run(latency=not args.no_latency)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
        return 0
    for split in ("holdout", "tuned"):
        rows = rep[split]
        n = rows["router"]["cases"]
        print(f"{split} ({n} cases){' - never tuned on' if split == 'holdout' else ''}")
        for key, _ in SYSTEMS:
            r = rows[key]
            ci = f"[{_pct(r['ci95'][0])}-{_pct(r['ci95'][1])}]"
            print(f"  {r['label']:40} {_pct(r['rate']):>5} {ci:>11}  {r['passed']:g}/{n}")
        v = rows["router"]["vs_bm25"]
        print(f"  router vs description match: {v['wins']} wins, {v['losses']} losses, exact McNemar p = {v['mcnemar_p']:.1g}")
    if "latency_ms" in rep:
        lat = rep["latency_ms"]
        print(f"latency: median {lat['median']} ms, p95 {lat['p95']} ms over {lat['routes']} routes ({lat['machine']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
