"""Turn a task into an ordered, explained chain of skills (design §7)."""

import hashlib
import re
import time
from pathlib import Path

from . import index, knowledge, models, project

TOKEN = re.compile(r"\w+", re.UNICODE)
PRIMARY, ALTERNATIVE, UNLISTED = 2.0, 0.7, 0.2
UNKNOWN_ROLE, UNKNOWN_ROLE_HARVESTED = 0.3, 0.5  # no role data: generic registry skill vs. local skill
INFERRED_FACTOR, MIN_SCORE, ASK_MARGIN, FLOW_BONUS = 0.8, 0.35, 0.10, 1.25
MIN_SHARED_TERMS = 2  # a skill without a manifest must share this many meaningful words with the task
KEEP_PRIORITY = ["build", "review", "verify", "plan", "specify", "operate", "research", "discover", "release", "learn"]


def _words(text: str) -> str:
    """Lowercase letters and digits, split like index.fold() but keeping accents."""
    return " ".join(re.findall(r"[^\W_]+", text.lower()))


def _positions(text: str, keywords: list[str]) -> list[int]:
    """Start offsets of whole-word and phrase keyword matches, ignoring case and hyphens. Text typed without accents
    is matched folded, as the index folds it; text with accents keeps them, since lời (words) is not lỗi (error)."""
    form = _words if _words(text) != index.fold(text) else index.fold
    words = form(text)
    out = []
    for k in keywords:
        m = re.search(rf"(?<!\S){re.escape(form(k))}(?!\S)", words) if form(k) else None
        if m:
            out.append(m.start())
    return out


def _hits(text: str, keywords: list[str]) -> int:
    return len(_positions(text, keywords))


def _terms(text: str) -> set[str]:
    return {t for t in TOKEN.findall(text.lower()) if len(t) > 1 and t not in index.STOP}


def _matched(text: str, keywords: list[str]) -> list[str]:
    return [k for k in keywords if _positions(text, [k])]


def _phase_order(tax) -> list[str]:
    return [p["id"] for p in tax["phases"]]


def target_phase(task: str, tax: dict) -> str:
    """Phase with the most keyword hits; ties go to the phase mentioned first ("add a model with tests" is build)."""
    best, key = "build", None
    for p in tax["phases"]:
        pos = _positions(task, p["keywords"])
        if pos:
            k = (-len(pos), min(pos))
            if key is None or k < key:
                best, key = p["id"], k
    return best


def task_size(task: str, tax: dict, given: str | None) -> str:
    if given:
        return given
    kw = tax.get("size_keywords", {})
    if _hits(task, kw.get("small", [])):
        return "small"
    if _hits(task, kw.get("large", [])):
        return "large"
    return "medium"


def phase_window(target: str, size: str, artifacts: list[str], role_window: list[str] | None = None) -> list[str]:
    return window_and_reason(target, size, artifacts, role_window)[0]


def window_and_reason(target: str, size: str, artifacts: list[str], role_window: list[str] | None = None,
                      role: str = "the lead role") -> tuple[list[str], str]:
    """The phases a route covers, and one sentence on why."""
    if target == "build":
        if size == "small":
            return ["build"], "small build task: build only"
        if role_window:
            return list(role_window), f"{role}'s build_window"
        start = "specify" if size == "large" else "plan"
        why = f"{size} build task: starts at {start}"
        if start == "specify" and "spec" in artifacts:
            start, why = "plan", "large build task with a spec in the project: starts at plan"
        if "tasks" in artifacts or (start == "plan" and "plan" in artifacts):
            found = "tasks" if "tasks" in artifacts else "plan"
            start, why = "build", f"{size} build task with {found} in the project: starts at build"
        order = ["specify", "plan", "build"]
        return order[order.index(start):] + ["verify", "review"], why + ", then verify and review"
    if target == "plan" and size == "large" and "spec" not in artifacts:
        return ["specify", "plan"], "large plan task without a spec: specify first"
    fixed = {"operate": (["operate", "build", "verify"], "operate task: fix, then verify"),
             "release": (["verify", "release"], "release task: verify first")}
    return fixed.get(target, ([target], f"{target} task: {target} only"))


def _role_mix(role, prof, proj) -> dict[str, float]:
    if role:
        return {role: 1.0}
    for src in (prof.get("roles") or {}, proj["role_signals"]):
        if src:
            total = sum(src.values())
            return {r: v / total for r, v in src.items()}
    return {"fullstack-developer": 1.0}


def _unsatisfied(skill: dict, proj: dict) -> list[str]:
    root = Path(proj["path"])
    return [r for r in skill.get("requires", []) if r.startswith("project:") and not (root / r[8:]).exists()]


def _install_hint(skill: dict, agent: str | None = None) -> str:
    """A project init first; for an agent other than Claude Code, a command that is not a Claude plugin one."""
    if agent and skill["source"] == "open-skill":
        return f"open-skill install {skill['name']} --agent {agent}"
    inst = skill.get("install") or {}
    for k, v in inst.items():
        if "init" in k:
            return v
    if agent and agent != "claude-code":
        other = [v for k, v in inst.items() if not k.startswith("claude")]
        if other:
            return other[0]
        if inst:  # only Claude Code commands; they would not work in this agent
            return f"see {skill.get('upstream') or skill['source']} (no install command for {agent})"
    return next(iter(inst.values()), f"install {skill['source']}")


def route(task: str, project_path: Path, reg, installed, role: str | None = None, size: str | None = None,
          model: str | None = None, record: bool = True, decisions: bool = False, agent: str | None = None,
          phase: str | None = None) -> dict:
    """decisions=True adds result["decisions"]: the phase window and the outcome of every candidate per phase.
    `phase` is the target phase when the caller knows it (an agent that read the conversation); ValueError if unknown."""
    tax = reg.taxonomy
    if phase is not None and phase not in _phase_order(tax):
        raise ValueError(f"unknown phase: {phase} (one of: {', '.join(_phase_order(tax))})")
    proj = project.inspect(Path(project_path), tax, reg.roles)
    prof = knowledge.load_profile()
    mix = _role_mix(role, prof, proj)
    given_size, size = size, task_size(task, tax, size)
    given_phase, target = phase, phase or target_phase(task, tax)
    lead = max(mix, key=mix.get)
    window, window_why = window_and_reason(target, size, proj["artifacts"], reg.roles.get(lead, {}).get("build_window"), lead)
    weights = knowledge.personal_weights()
    phase_kw = {p["id"]: p["keywords"] for p in tax["phases"]}
    size_kw = tax.get("size_keywords", {}).get(size, [])
    phase_words = [] if given_phase else _matched(task, phase_kw.get(target, []))
    phase_from = "given" if given_phase else ("keywords" if phase_words else "guessed")
    size_from = "given" if given_size else ("keywords" if _matched(task, size_kw) else "default")
    task_terms = _terms(task)

    conn = index.build_index(reg, installed)
    hits = dict(index.search(conn, task, limit=200))
    by_id = {}
    for i in installed:
        by_id.setdefault(i.id, i)

    def role_prior(sid: str, phase: str, manifest: dict | None) -> tuple[float, str]:
        total, notes = 0.0, []
        for r, share in mix.items():
            entry = (reg.roles.get(r, {}).get("phases") or {}).get(phase) or {}
            if sid in entry.get("primary", []):
                total += share * PRIMARY
                notes.append(f"primary for {r}")
            elif sid in entry.get("alternatives", []):
                total += share * ALTERNATIVE
                notes.append(f"alternative for {r}")
            elif manifest and manifest.get("roles"):
                total += share * manifest["roles"].get(r, UNLISTED)
            else:
                total += share * (UNKNOWN_ROLE if manifest else UNKNOWN_ROLE_HARVESTED)
        return total, ", ".join(notes)

    chain, chosen, missing, asks, trace = [], [], {}, {}, []

    def decide(phase: str, sid: str, outcome: str, **extra):
        trace.append({"phase": phase, "id": sid, "outcome": outcome, **extra})
    available = set(proj["artifacts"])  # artifacts in the repo plus those produced by earlier steps
    for phase in window:
        cands = []
        for sid, inst in by_id.items():
            manifest = reg.skills.get(sid)
            if manifest:
                if phase not in manifest.get("phases", []):
                    decide(phase, sid, "wrong-phase", phases=manifest.get("phases", []))
                    continue
                if size not in manifest.get("task_size", [size]):
                    decide(phase, sid, "wrong-size", sizes=manifest["task_size"])
                    continue
                unmet = _unsatisfied(manifest, proj)
                if unmet:
                    decide(phase, sid, "requirement-unmet", needs=[u[8:] for u in unmet])
                    continue
            elif not _hits(inst.description, phase_kw.get(phase, [])):
                decide(phase, sid, "no-phase-keywords")
                continue
            elif len(task_terms & _terms(inst.description)) < MIN_SHARED_TERMS:
                decide(phase, sid, "few-shared-terms", shared=len(task_terms & _terms(inst.description)))
                continue
            prior, note = role_prior(sid, phase, manifest)
            s = hits.get(sid, 0.0)
            rel = 1 + 3 * s / (s + 4)  # saturating: strong text matches help, but cannot outweigh role and phase
            personal = weights.get(sid, 0.0)
            native = bool(manifest and proj["native"] and manifest["source"] == proj["native"])
            flow = bool(manifest and set(manifest.get("consumes", [])) & available)
            score = rel * prior * (1 + personal) * (INFERRED_FACTOR if inst.inferred else 1.0) * (FLOW_BONUS if flow else 1.0)
            why = [f"phase {phase}", f"role prior {prior:.2f}" + (f" ({note})" if note else ""), f"text {rel:.2f}"]
            if personal:
                why.append(f"your history {personal:+.2f}")
            if native:
                why.append(f"native {proj['native']}")
            if flow:
                why.append("consumes " + ", ".join(sorted(set(manifest["consumes"]) & available)))
            if inst.inferred:
                why.append("inferred from description")
            cands.append((native, score, sid, inst, manifest, "; ".join(why)))
        # The project's native framework wins its phases outright (design §5.1); otherwise best score.
        cands.sort(key=lambda c: (c[0], c[1]), reverse=True)
        valid = []
        for c in cands:
            _, score, sid, _, manifest, _ = c
            conflicts = set((manifest or {}).get("conflicts", []))
            clash = [x for x in chosen if sid in set((reg.skills.get(x) or {}).get("conflicts", [])) or x in conflicts]
            if sid in chosen:
                decide(phase, sid, "already-chosen")
            elif clash:
                decide(phase, sid, "conflict", score=round(score, 3), conflicts_with=clash)
            elif score < MIN_SCORE:
                decide(phase, sid, "below-minimum", score=round(score, 3), minimum=MIN_SCORE)
            else:
                valid.append(c)
        if valid:
            native, score, sid, inst, manifest, why = valid[0]
            decide(phase, sid, "chosen", score=round(score, 3), why=why)
            for c in valid[1:]:
                decide(phase, c[2], "lower-score", score=round(c[1], 3), winner=sid, winner_score=round(score, 3),
                     native_winner=native and not c[0])
            step = {"phase": phase, "id": sid, "invoke": inst.invoke, "kind": (manifest or {}).get("kind", "skill"),
                    "score": round(score, 3), "why": why}
            if len(valid) > 1 and valid[1][0] == native and valid[1][1] >= score * (1 - ASK_MARGIN):
                # Only the phase that carries the user's intent is worth a question; elsewhere note the runner-up.
                if phase == target:
                    step["ask"] = [sid, valid[1][2]]
                    asks[phase] = step["ask"]
                else:
                    step["runner_up"] = valid[1][2]
            chain.append(step)
            chosen.append(sid)
            available |= set((manifest or {}).get("produces", []))
        for r in mix:
            entry = (reg.roles.get(r, {}).get("phases") or {}).get(phase) or {}
            for sid in entry.get("primary", []):
                manifest = reg.skills.get(sid)
                if not manifest or sid in chosen or sid in missing:
                    continue
                reason = "not installed" if sid not in by_id else None
                unmet = _unsatisfied(manifest, proj)
                if unmet:
                    reason = f"needs {', '.join(u[8:] for u in unmet)} in the project"
                if reason:
                    missing[sid] = {"id": sid, "phase": phase, "reason": reason,
                                    "install": _install_hint(manifest, agent),
                                    "optional": phase != target}

    advice = None
    if size == "small" and len(chain) <= 1 and target == "build":
        chain, advice = [], "do directly"
        for d in trace:
            if d["outcome"] == "chosen":
                d["outcome"] = "do-directly"

    prof_m = models.resolve(model, reg.models)
    max_steps = (prof_m.get("chain") or {}).get("max_steps")
    if max_steps and len(chain) > max_steps:
        keep = sorted(chain, key=lambda s: KEEP_PRIORITY.index(s["phase"]) if s["phase"] in KEEP_PRIORITY else 99)
        kept = {id(s) for s in keep[:max_steps]}
        chain = [s for s in chain if id(s) in kept]
        final = {(s["phase"], s["id"]) for s in chain}
        for d in trace:
            if d["outcome"] == "chosen" and (d["phase"], d["id"]) not in final:
                d.update(outcome="trimmed", max_steps=max_steps)
    effort = (prof_m.get("effort") or {}).get(size)
    for s in chain:
        s["effort"] = effort

    proj_key = f"project:{proj['path']}"
    wanted = {f"skill:{s['id']}" for s in chain} | {f"role:{r}" for r in mix} | {"role:*", proj_key}
    wanted |= {f"phase:{p}" for p in window}
    nodes = [k for k in knowledge.load_knowledge() if wanted & set(k.get("applies_to", []))]
    nodes.sort(key=lambda k: str(k.get("created", "")), reverse=True)  # newest first...
    nodes.sort(key=lambda k: k.get("type") not in ("lesson", "pitfall"))  # ...lessons and pitfalls before the rest

    rid = "r-" + time.strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha1(f"{task}{time.time()}".encode()).hexdigest()[:6]
    result = {
        "route_id": rid,
        "task": task,
        "agent": agent,
        "role": mix,
        "size": size,
        "target_phase": target,
        "phase_from": phase_from,
        "project": {k: proj[k] for k in ("path", "native", "artifacts", "codegraph")},
        "chain": chain,
        "advice": advice,
        "knowledge": [{"id": k["id"], "type": k.get("type"), "text": k.get("text", "")} for k in nodes[:5]],
        "missing": list(missing.values()),
        "model": {"profile": prof_m["id"], "matched_by": prof_m["matched_by"], "effort": effort,
                  "max_steps": max_steps, "addenda": prof_m.get("addenda", []), "avoid": prof_m.get("avoid", []),
                  "traits": prof_m.get("traits", {})},
    }
    if decisions:
        result["decisions"] = {
            "phase": {"target": target, "from": phase_from, "keywords": phase_words},
            "size": {"size": size, "from": size_from, "keywords": _matched(task, size_kw) if size_from == "keywords" else []},
            "window": window, "window_reason": window_why, "candidates": trace}
    if record:
        knowledge.record({"type": "proposed", "route_id": rid, "task": task,
                          "chain": [{"id": s["id"], "invoke": s["invoke"]} for s in chain]})
    return result


def _reason_text(d: dict, size: str) -> str:
    p, code = d["phase"], d["outcome"]
    return {
        "wrong-size": lambda: f"made for {', '.join(d.get('sizes', []))} tasks; this one is {size}",
        "requirement-unmet": lambda: f"needs {', '.join(d.get('needs', []))} in the project",
        "no-phase-keywords": lambda: f"no manifest, and its description has no {p} keywords",
        "few-shared-terms": lambda: f"no manifest, and its description shares {d.get('shared')} word(s) with the task "
                                    f"(needs {MIN_SHARED_TERMS})",
        "conflict": lambda: f"conflicts with {', '.join(d.get('conflicts_with', []))}, already in the chain",
        "below-minimum": lambda: f"score {d.get('score')} is below the minimum {d.get('minimum')}",
        "lower-score": lambda: f"score {d.get('score')} lost to {d.get('winner')} ({d.get('winner_score')})"
                               + ("; the project's native framework wins its phases" if d.get("native_winner") else ""),
        "trimmed": lambda: f"won with score {d.get('score')}, then dropped to fit the model's {d.get('max_steps')}-step limit",
        "do-directly": lambda: f"won with score {d.get('score')}, but the task is small enough to do directly",
    }[code]()


def why_not(result: dict, skill_id: str, reg, installed) -> dict:
    """Why a skill is not in the chain, from a route(..., decisions=True) result. KeyError for unknown skills."""
    have = {i.id for i in installed}
    if skill_id not in reg.skills and skill_id not in have:
        raise KeyError(skill_id)
    mine = [d for d in result["decisions"]["candidates"] if d["id"] == skill_id]
    chosen = next((d["phase"] for d in mine if d["outcome"] == "chosen"), None)
    out = {"id": skill_id, "chosen": chosen, "reasons": []}
    if chosen:
        return out
    if skill_id not in have:
        hint = _install_hint(reg.skills[skill_id], result.get("agent"))
        out["reasons"].append({"code": "not-installed", "text": f"not installed → {hint}"})
        return out
    window = result["decisions"]["window"]
    relevant = [d for d in mine if d["outcome"] not in ("wrong-phase", "already-chosen")]
    if not relevant:
        phases = (reg.skills.get(skill_id) or {}).get("phases", [])
        out["reasons"].append({"code": "wrong-phase", "text": f"acts in {', '.join(phases) or 'no phase'}; "
                                                              f"this task's phase window is {', '.join(window)}"})
    for d in relevant:
        out["reasons"].append({"code": d["outcome"], "phase": d["phase"],
                               "text": f"[{d['phase']}] {_reason_text(d, result['size'])}"})
    return out
