import argparse
import json
import sys
from pathlib import Path

import yaml

from . import __version__, agents, evals, frontmatter, generate, graph_html, index, install, knowledge, lint, paths, registry, route, scan, upgrade, userdata


def _registry(args):
    overlays = list(knowledge.load_profile().get("overlays", [])) + list(args.overlay or [])
    return registry.load(Path(args.registry) if args.registry else None, overlays=overlays)


def _print(obj, as_json=True):
    print(json.dumps(obj, indent=2, ensure_ascii=False) if as_json else obj)


def cmd_validate(args):
    errors = registry.validate(_registry(args))
    for e in errors:
        print(e, file=sys.stderr)
    print(f"{len(errors)} error(s)")
    return 1 if errors else 0


def cmd_lint(args):
    if args.installed:
        report = lint.health(scan.scan(_registry(args)))
        if args.format == "json":
            _print(report)
            return 0
        print(f"{'source':34} {'skills':>6} {'errors':>6} {'warnings':>8}")
        for src, row in report.items():
            print(f"{src:34} {row['skills']:>6} {row['errors']:>6} {row['warnings']:>8}")
            for w in row["worst"][:3]:
                print(f"    {w}")
        return 0
    targets = args.paths or [str(paths.data_root() / "skills")]
    findings = lint.lint_paths(targets)
    errors = [f for f in findings if f.severity == "error"]
    if args.format == "json":
        _print([f.__dict__ for f in findings])
    else:
        for f in findings:
            print(f"{f.path}: {f.severity} [{f.rule}] {f.message} ({f.source})")
        print(f"{len(errors)} error(s), {len(findings) - len(errors)} warning(s)")
    return 1 if errors or (args.strict and findings) else 0


def cmd_scan(args):
    reg = _registry(args)
    if args.memory:
        print(f"imported {knowledge.import_agent_memory()} memory file(s)")
        return 0
    if args.agent and _agent_arg(reg, args.agent) is None:
        return 2
    items = scan.scan(reg, Path(args.project) if args.project else None, agent=args.agent)
    if args.json:
        _print([i.__dict__ for i in items])
    else:
        for i in items:
            print(f"{i.invoke:45} {i.id:45} {','.join(i.agents)}{'  (inferred)' if i.inferred else ''}")
        print(f"{len(items)} skill(s)")
    return 0


def _agent_rows(reg, project: Path | None) -> list[dict]:
    installed = scan.scan(reg, project)
    rows = []
    for aid, a in sorted(reg.agents.items()):
        glob, proj = agents.folders(a, "global"), agents.folders(a, "project", project)
        rows.append({"id": aid, "name": a.get("name", aid), "detected": agents.detected(a),
                     "skills": sum(aid in i.agents for i in installed), "docs": a.get("docs"),
                     "install_to": {"global": str(glob[0]) if glob else None, "project": str(proj[0]) if proj else None},
                     "reads": [str(p) for p in glob + proj]})
    return rows


def cmd_agents(args):
    rows = _agent_rows(_registry(args), Path(args.project) if args.project else None)
    if args.json:
        _print(rows)
        return 0
    for r in rows:
        where = r["install_to"]["project"] or r["install_to"]["global"]
        print(f"{'✓' if r['detected'] else '·'} {r['id']:16} {r['name'][:28]:28} {r['skills']:3} skill(s)  {where}")
    print(f"{sum(r['detected'] for r in rows)} of {len(rows)} agent(s) detected")
    return 0


def _agent_arg(reg, aid: str) -> dict | None:
    if aid not in reg.agents:
        print(f"unknown agent {aid}; known: {', '.join(sorted(reg.agents))}", file=sys.stderr)
        return None
    return reg.agents[aid]


def cmd_install(args):
    agent = _agent_arg(_registry(args), args.agent)
    if agent is None:
        return 2
    try:
        p = install.plan(install.resolve_source(args.skill), agent, Path(args.project) if args.project else None,
                         "symlink" if args.symlink else "copy")
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if p.action == "refuse":
        print(p.reason, file=sys.stderr)
        return 1
    if p.action == "unchanged":
        print(f"unchanged: {p.reason}")
        return 0
    if not args.dry_run:
        install.apply(p)
    print(f"{'would install' if args.dry_run else 'installed'} {p.source.name} for {p.agent} ({p.mode}) → {p.dest}")
    return 0


def cmd_build(args):
    reg = _registry(args)
    root = Path(args.root) if args.root else paths.data_root()
    if args.check:
        stale = generate.stale(reg, root)
        for p in stale:
            print(f"stale: {p.relative_to(root)}", file=sys.stderr)
        return 1 if stale else 0
    written = generate.write_all(reg, root)
    print(f"wrote {len(written)} file(s) + dist/index.db")
    return 0


def cmd_search(args):
    reg = _registry(args)
    installed = scan.scan(reg, Path(args.project) if args.project else None)
    have = {i.id for i in installed}
    known = {"role": set(reg.roles), "phase": {p["id"] for p in reg.taxonomy["phases"]},
             "source": set(reg.adapters) | {i.id.split("/")[0] for i in installed}}
    for opt, values in known.items():
        v = getattr(args, opt)
        if v and v not in values:
            print(f"unknown {opt}: {v} (one of: {', '.join(sorted(values))})", file=sys.stderr)
            return 2
    if args.query:
        hits = index.search(index.build_index(reg, installed), args.query, limit=len(reg.skills) + len(installed))
    elif args.role or args.phase or args.source or args.installed:
        hits = [(sid, None) for sid in sorted(set(reg.skills) | have)]
    else:
        print("give a query or at least one filter", file=sys.stderr)
        return 2
    hits = [(sid, score) for sid, score in hits
            if index.matches(reg, sid, args.role, args.phase, args.source) and (sid in have or not args.installed)]
    for sid, score in hits[:args.limit]:
        print(f"{'-' if score is None else f'{score:.2f}':>7}  {sid}{'' if sid in have else '  (not installed)'}")
    return 0


def _explain(r) -> str:
    lines = [f"route {r['route_id']}  role={r['role']}  size={r['size']}  target={r['target_phase']}",
             f"project native={r['project']['native']} artifacts={r['project']['artifacts']}",
             f"model profile={r['model']['profile']} ({r['model']['matched_by']}) effort={r['model']['effort']}"]
    d = r.get("decisions")
    if d:
        ph, sz = d["phase"], d["size"]
        lines.append(f"target {ph['target']} from phase keywords: {', '.join(ph['keywords'])}" if ph["keywords"]
                     else f"target {ph['target']}: no phase keywords, the default")
        lines.append({"given": f"size {sz['size']}: given",
                      "keywords": f"size {sz['size']} from size keywords: {', '.join(sz['keywords'])}",
                      "default": f"size {sz['size']}: no size keywords, the default"}[sz["from"]])
        lines.append(f"phase window: {' → '.join(d['window'])} ({d['window_reason']})")
    if r["advice"]:
        lines.append(f"advice: {r['advice']}")
    for i, s in enumerate(r["chain"], 1):
        lines.append(f"{i}. [{s['phase']}] {s['invoke']}  score={s['score']}  — {s['why']}")
        if s.get("ask"):
            lines.append(f"   close call on the main step, ask the user: {s['ask']}")
        losers = sorted((c for c in (d or {}).get("candidates", []) if c["phase"] == s["phase"] and c["outcome"] == "lower-score"),
                        key=lambda c: -c["score"])[:3]
        if losers:
            lines.append("   runner-ups: " + ", ".join(
                f"{c['id']} {c['score']}" + (" (close call)" if c["id"] == s.get("runner_up") else "") for c in losers))
        elif s.get("runner_up"):
            lines.append(f"   runner-up: {s['runner_up']}")
    for m in r["missing"]:
        lines.append(f"missing: {m['id']} ({m['reason']}) → {m['install']}")
    for k in r["knowledge"]:
        lines.append(f"knowledge [{k['type']}]: {k['text']}")
    for a in r["model"]["addenda"]:
        lines.append(f"model note: {a}")
    return "\n".join(lines)


def _why_not(args, reg, proj, installed) -> int:
    sid = next((i.id for i in installed if i.invoke == args.why_not), args.why_not)
    r = route.route(args.task, proj, reg, installed, role=args.role, size=args.size, model=args.model,
                    record=False, decisions=True)
    try:
        w = route.why_not(r, sid, reg, installed)
    except KeyError:
        print(f"unknown skill: {args.why_not} (see open-skill search)", file=sys.stderr)
        return 2
    if w["chosen"]:
        print(f"{sid} is in the chain, for phase {w['chosen']}")
        return 0
    print(f"{sid} is not in the chain for: {args.task}")
    for x in w["reasons"]:
        print(f"  - {x['text']}")
    return 0


def cmd_route(args):
    reg = _registry(args)
    proj = Path(args.project or ".")
    installed = scan.scan(reg, proj)
    if args.why_not:
        return _why_not(args, reg, proj, installed)
    r = route.route(args.task, proj, reg, installed, role=args.role, size=args.size, model=args.model,
                    record=not args.no_record, decisions=args.explain)
    _print(_explain(r) if args.explain else r, as_json=not args.explain)
    return 0


def cmd_graph(args):
    reg = _registry(args)
    if args.format == "mermaid":
        text = index.graph_mermaid(reg)
    else:
        g = index.graph_json(reg, scan.scan(reg))
        text = graph_html.graph_html(g) if args.format == "html" else json.dumps(g, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text, end="")
    return 0


def cmd_doctor(args):
    reg = _registry(args)
    installed = scan.scan(reg, Path(args.project) if args.project else None)
    by_src: dict[str, int] = {}
    for i in installed:
        by_src[i.id.split("/")[0]] = by_src.get(i.id.split("/")[0], 0) + 1
    print(f"open-skill {__version__}  registry={paths.data_root()}  home={knowledge.home()}")
    found = [a for a in reg.agents.values() if agents.detected(a)]
    seen = ", ".join(f"{a['id']} ({sum(a['id'] in i.agents for i in installed)} skills)" for a in found)
    print(f"  agents: {seen or 'none detected'} → open-skill agents")
    for a in found:
        if not any(i.id == "open-skill/open-skill-router" and a["id"] in i.agents for i in installed):
            print(f"  · {a['id']} does not see the open-skill router → open-skill install open-skill-router --agent {a['id']}")
    for src, a in sorted(reg.adapters.items()):
        n = by_src.get(src, 0)
        hint = "" if n else f"  → {next(iter((a.get('install') or {}).values()), 'see ' + a.get('upstream', ''))}"
        print(f"  {'✓' if n else '·'} {src:22} {n:3} installed / {len(a['skills'])} described{hint}")
    print(f"  harvested (no manifest): {by_src.get('harvested', 0)}")
    rep = lint.health(installed)
    errs = sum(r["errors"] for r in rep.values())
    warns = sum(r["warnings"] for r in rep.values())
    print(f"  skill health: {errs} error(s), {warns} warning(s) across installed skills → open-skill lint --installed")
    names: dict[str, list[str]] = {}
    for i in installed:
        names.setdefault(i.invoke.split(":")[-1], []).append(i.invoke)
    dupes = {k: v for k, v in names.items() if len(v) > 1}
    for k, v in dupes.items():
        print(f"  ! same skill name from several sources: {', '.join(v)}")
    if not (knowledge.home() / "profile.yaml").exists():
        print("  · no profile yet → open-skill init")
    if userdata.pending(knowledge.home()):
        print(f"  ! your data uses schema {userdata.data_version(knowledge.home())} → open-skill upgrade")
    if knowledge.proposals():
        print(f"  ! {len(knowledge.proposals())} seed update(s) to review → open-skill seeds diff")
    return 0


def _parse_roles(items) -> dict[str, float]:
    out = {}
    for item in items or []:
        name, _, w = item.partition("=")
        out[name] = float(w or 1.0)
    return out


def cmd_init(args):
    reg = _registry(args)
    roles = _parse_roles(args.role)
    if not roles and sys.stdin.isatty():
        known = ", ".join(sorted(reg.roles))
        answer = input(f"Your roles, e.g. data-engineer=0.7,data-analyst=0.3\n({known})\n> ")
        roles = _parse_roles([x.strip() for x in answer.split(",") if x.strip()])
    unknown = [r for r in roles if r not in reg.roles]
    if unknown:
        print(f"unknown role(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    profile = {"roles": roles, "stack": args.stack or [], "build_framework": args.framework, "language": args.language}
    seeds = {rid: r.get("seeds", []) for rid, r in reg.roles.items()}
    print(f"profile written to {knowledge.init(profile, seeds)}")
    return 0


def cmd_learn(args):
    try:
        nid = knowledge.learn(args.text, args.applies_to.split(","), type_=args.type, force=args.force)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    print(nid)
    return 0


def cmd_forget(args):
    ok = knowledge.forget(args.id)
    print("forgotten" if ok else "not found")
    return 0 if ok else 1


def cmd_feedback(args):
    knowledge.record({"type": "feedback", "route_id": args.route_id, "ran": [x for x in args.ran.split(",") if x],
                      "outcome": args.outcome, "note": args.note})
    print("recorded")
    return 0


def cmd_export(args):
    print(knowledge.export(Path(args.dest)))
    return 0


def cmd_backup(args):
    home = knowledge.home()
    if args.list:
        for b in userdata.list_backups(home):
            print(b)
        return 0
    dest = userdata.backup(home, "manual")
    print(dest or f"nothing to back up in {home}")
    return 0


def cmd_restore(args):
    try:
        safety = userdata.restore(knowledge.home(), Path(args.archive))
    except userdata.UnsafeBackupError as e:
        print(e, file=sys.stderr)
        return 2
    print(f"restored {args.archive}" + (f"; previous state saved to {safety}" if safety else ""))
    return 0


def cmd_migrate(args):
    home = knowledge.home()
    actions = userdata.migrate(home, dry_run=args.dry_run)
    if not actions:
        print(f"{home} is up to date (data schema {userdata.data_version(home)})")
        return 0
    print(("dry run, nothing changed:\n" if args.dry_run else "") + "\n".join(actions))
    return 0


def cmd_seeds(args):
    if args.action in ("diff", "accept", "keep"):
        return _seed_decision(args)
    reg = _registry(args)
    roles = list(knowledge.load_profile().get("roles", {}))
    if not roles:
        print("no roles in your profile yet; run: open-skill init --role <role>")
        return 1
    seeds = {rid: r.get("seeds", []) for rid, r in reg.roles.items()}
    actions = knowledge.sync_seeds(roles, seeds, dry_run=args.dry_run)
    print("\n".join(actions) if actions else "starter knowledge is up to date")
    return 0


def _seed_decision(args):
    import difflib

    pending = knowledge.proposals()
    ids = [args.seed_id] if args.seed_id else sorted(pending)
    if not ids:
        print("no seed updates waiting for review")
        return 0
    for sid in ids:
        if sid not in pending:
            print(f"no proposal for {sid}", file=sys.stderr)
            return 1
        if args.action == "diff":
            note = next((n for n in knowledge.load_knowledge() if n.get("seed_id") == sid), {"text": ""})
            diff = difflib.unified_diff(note["text"].splitlines(), pending[sid].splitlines(),
                                        f"{sid} (yours)", f"{sid} (upstream)", lineterm="")
            print("\n".join(diff))
        elif args.action == "accept":
            print(f"accepted upstream wording for {sid}; your version is in {knowledge.accept_proposal(sid)}")
        else:
            knowledge.keep_mine(sid)
            print(f"kept your version of {sid}")
    return 0


def cmd_upgrade(args):
    if args.rollback:
        try:
            print(upgrade.rollback())
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            return 1
        return 0
    reg = _registry(args)
    seeds = {rid: r.get("seeds", []) for rid, r in reg.roles.items()}
    actions = upgrade.upgrade(seeds, dry_run=args.dry_run)
    print(("dry run, nothing changed:\n" if args.dry_run else "") + ("\n".join(actions) or "already up to date"))
    return 0


def cmd_status(args):
    home = knowledge.home()
    v = userdata.data_version(home)
    prof = knowledge.load_profile()
    info = {
        "open_skill": __version__,
        "registry": str(paths.data_root()),
        "home": str(home),
        "data_schema": v,
        "cli_schema": userdata.SCHEMA_VERSION,
        "pending_migrations": len(userdata.pending(home)),
        "roles": prof.get("roles", {}),
        "notes": len(knowledge.load_knowledge()) if (home / "knowledge").exists() else 0,
        "seed_updates_to_review": len(knowledge.proposals()),
        "backups": len(userdata.list_backups(home)),
    }
    if args.json:
        _print(info)
    else:
        for k, val in info.items():
            print(f"{k:24} {val}")
        if v > userdata.SCHEMA_VERSION:
            print("! your data is newer than this CLI; upgrade open-skill before writing")
        elif info["pending_migrations"]:
            print("! run: open-skill upgrade")
        if info["seed_updates_to_review"]:
            print("! review: open-skill seeds diff")
    return 0


def _eval_triggers(args, reg):
    import shutil

    sets = evals.load_trigger_sets(Path(args.cases) if args.cases else None)
    if args.agent == "claude":
        if not shutil.which("claude"):
            print("the claude CLI is not on PATH; install Claude Code or use the default lexical proxy", file=sys.stderr)
            return 2
        rep = evals.trigger_report_agent(sets, evals.claude_runner(), runs=args.runs)
        if args.format == "json":
            _print(rep)
            return 0
        print(f"agent run: claude, {args.runs} runs per query, trigger when rate >= 0.5")
        for skill, r in rep.items():
            t, v = r["train"], r["validation"]
            print(f"{skill:28} train P {t['precision']:.2f} R {t['recall']:.2f} | validation P {v['precision']:.2f} R {v['recall']:.2f}")
        return 0
    rep = evals.trigger_report_lexical(sets, evals.skill_descriptions(reg))
    if args.format == "json":
        _print(rep)
        return 0
    print("lexical proxy of description-based triggering (not a model run); failures listed for tuning queries only")
    for skill, r in rep.items():
        m, h = r["train"], r["validation"]
        print(f"{skill:28} tune P {m['precision']:.2f} R {m['recall']:.2f} | holdout P {h['precision']:.2f} R {h['recall']:.2f}")
        for q in m["missed"]:
            print(f"    missed: {q}")
        for q in m["false_alarms"]:
            print(f"    false alarm: {q}")
    return 0


def cmd_eval(args):
    reg = _registry(args)
    if args.kind == "triggers":
        return _eval_triggers(args, reg)
    cases = evals.load_routing_cases(Path(args.cases) if args.cases else None)
    rep = evals.routing_report(cases, reg, evals.all_installed(reg))
    if args.format == "json":
        _print(rep)
    else:
        for role, row in rep["by_role"].items():
            print(f"{role:30} {row['passed']}/{row['cases']}")
        for r in rep["results"]:
            for f in r["failures"]:
                print(f"FAIL {r['id']}: {f}")
        print(f"{rep['passed']}/{rep['cases']} passed ({rep['pass_rate']:.0%})")
    return 0 if rep["passed"] == rep["cases"] else 1


def _upstream_skills(src_dir: Path) -> dict[str, str]:
    found = {}
    for p in sorted(Path(src_dir).rglob("SKILL.md")):
        if ".git" in p.parts:
            continue
        meta, _ = frontmatter.parse(p.read_text(errors="replace"))
        found[p.parent.name] = str(meta.get("description") or "")  # agents invoke skills by folder name
    return found


def cmd_adapter(args):
    reg = _registry(args)
    up = _upstream_skills(Path(args.src))
    if args.action == "draft":
        skills = [{"name": n, "description": d, "phases": [route.target_phase(d, reg.taxonomy)]} for n, d in up.items()]
        print(yaml.safe_dump({"source": args.source, "upstream": "", "license": "", "skills": skills},
                             sort_keys=False, allow_unicode=True, width=120))
        return 0
    have = {s["name"] for s in reg.adapters.get(args.source, {}).get("skills", [])}
    added, removed = sorted(set(up) - have), sorted(have - set(up))
    for n in added:
        print(f"+ {n}: upstream skill missing from adapter")
    for n in removed:
        print(f"- {n}: adapter skill no longer upstream")
    return 1 if added or removed else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="open-skill", description="Open Skill Standard CLI")
    p.add_argument("--version", action="version", version=f"open-skill {__version__}")
    p.add_argument("--registry", help="data root containing registry/ and spec/ (default: bundled)")
    p.add_argument("--overlay", action="append", help="extra registry layer (org or personal), repeatable")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate", help="check registry schemas and references").set_defaults(fn=cmd_validate)
    s = sub.add_parser("lint", help="lint SKILL.md files against the Agent Skills spec and prompting guidance")
    s.add_argument("paths", nargs="*")
    s.add_argument("--strict", action="store_true", help="fail on warnings too")
    s.add_argument("--installed", action="store_true", help="health report of every installed skill, by source")
    s.add_argument("--format", choices=["text", "json"], default="text")
    s.set_defaults(fn=cmd_lint)
    s = sub.add_parser("scan", help="list installed skills")
    s.add_argument("--project")
    s.add_argument("--json", action="store_true")
    s.add_argument("--memory", action="store_true", help="import Claude Code memory files into knowledge")
    s.add_argument("--agent", help="only skills this agent sees, by the names it invokes them (see registry/agents)")
    s.set_defaults(fn=cmd_scan)
    s = sub.add_parser("agents", help="coding agents on this machine, the skills each sees and where installs go")
    s.add_argument("--project", help="also show the project skill folder of each agent")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_agents)
    s = sub.add_parser("install", help="install a core skill or a local skill folder for an agent (never overwrites)")
    s.add_argument("skill", help="core skill name (open-skill-router, ...) or a folder containing SKILL.md")
    s.add_argument("--agent", required=True, help="agent id, see: open-skill agents")
    s.add_argument("--project", help="install into this project's skill folder instead of the user folder")
    how = s.add_mutually_exclusive_group()
    how.add_argument("--copy", action="store_true", help="copy the files (default)")
    how.add_argument("--symlink", action="store_true", help="link to the source folder")
    s.add_argument("--dry-run", action="store_true", help="show what would happen without changing anything")
    s.set_defaults(fn=cmd_install)
    s = sub.add_parser("build", help="regenerate playbooks, schemas and dist/")
    s.add_argument("--root")
    s.add_argument("--check", action="store_true", help="exit 1 if generated files are stale")
    s.set_defaults(fn=cmd_build)
    s = sub.add_parser("search", help="full-text search over skills")
    s.add_argument("query", nargs="?", help="words to search for; leave out to list every skill the filters keep")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--project")
    s.add_argument("--role", help="only skills this role's pack lists or whose manifest names it")
    s.add_argument("--phase", help="only skills that act in this phase")
    s.add_argument("--source", help="only skills from this adapter source (or 'harvested')")
    s.add_argument("--installed", action="store_true", help="only skills installed on this machine")
    s.set_defaults(fn=cmd_search)
    s = sub.add_parser("route", help="choose and order skills for a task")
    s.add_argument("task")
    s.add_argument("--project")
    s.add_argument("--role")
    s.add_argument("--size", choices=["small", "medium", "large"])
    s.add_argument("--model")
    s.add_argument("--explain", action="store_true")
    s.add_argument("--no-record", action="store_true")
    s.add_argument("--why-not", metavar="SKILL", help="explain why a skill (id or invoke name) is not in the chain")
    s.set_defaults(fn=cmd_route)
    s = sub.add_parser("graph", help="export the skill graph")
    s.add_argument("--format", choices=["mermaid", "json", "html"], default="mermaid")
    s.add_argument("--out", help="write to this file instead of stdout")
    s.set_defaults(fn=cmd_graph)
    s = sub.add_parser("doctor", help="what is installed, missing, duplicated")
    s.add_argument("--project")
    s.set_defaults(fn=cmd_doctor)
    s = sub.add_parser("init", help="create your profile and seed knowledge")
    s.add_argument("--role", action="append", help="role or role=weight, repeatable")
    s.add_argument("--stack", action="append")
    s.add_argument("--framework", choices=["spec-kit", "bmad-method", "superpowers"])
    s.add_argument("--language")
    s.set_defaults(fn=cmd_init)
    s = sub.add_parser("learn", help="remember a lesson or preference")
    s.add_argument("text")
    s.add_argument("--applies-to", required=True, help="comma list: skill:<id>,role:<id>,project:<path>,phase:<id>")
    s.add_argument("--type", default="lesson", choices=["preference", "lesson", "glossary", "project-fact", "pitfall"])
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_learn)
    s = sub.add_parser("forget", help="delete a knowledge node")
    s.add_argument("id")
    s.set_defaults(fn=cmd_forget)
    s = sub.add_parser("feedback", help="record what actually ran for a route")
    s.add_argument("route_id")
    s.add_argument("--ran", default="")
    s.add_argument("--outcome", choices=["ok", "fail"], default="ok")
    s.add_argument("--note")
    s.set_defaults(fn=cmd_feedback)
    s = sub.add_parser("export", help="zip profile + knowledge (no events)")
    s.add_argument("dest")
    s.set_defaults(fn=cmd_export)
    s = sub.add_parser("backup", help="zip ~/.open-skill into its backups/ folder")
    s.add_argument("--list", action="store_true", help="list existing backups")
    s.set_defaults(fn=cmd_backup)
    s = sub.add_parser("restore", help="replace ~/.open-skill with a backup (the current state is backed up first)")
    s.add_argument("archive")
    s.set_defaults(fn=cmd_restore)
    s = sub.add_parser("migrate", help="upgrade ~/.open-skill to the current data schema (backs up first)")
    s.add_argument("--dry-run", action="store_true", help="show what would change without changing anything")
    s.set_defaults(fn=cmd_migrate)
    s = sub.add_parser("seeds", help="sync starter knowledge for your roles; your edits are never overwritten")
    s.add_argument("action", choices=["sync", "diff", "accept", "keep"])
    s.add_argument("seed_id", nargs="?", help="for diff/accept/keep: one seed id (default: all waiting)")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_seeds)
    s = sub.add_parser("upgrade", help="after pulling a new release: migrate your data and sync starter knowledge safely")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--rollback", action="store_true", help="restore the state from before the last upgrade")
    s.set_defaults(fn=cmd_upgrade)
    s = sub.add_parser("status", help="versions of the CLI and your data, and anything waiting for you")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_status)
    s = sub.add_parser("eval", help="measure routing quality against labeled cases")
    s.add_argument("kind", choices=["routing", "triggers"])
    s.add_argument("--cases", help="routing: a YAML file of cases; triggers: a folder of trigger sets (default: bundled)")
    s.add_argument("--format", choices=["text", "json"], default="text")
    s.add_argument("--agent", choices=["claude"], help="triggers: run queries through a real agent instead of the proxy")
    s.add_argument("--runs", type=int, default=3, help="triggers with --agent: runs per query")
    s.set_defaults(fn=cmd_eval)
    s = sub.add_parser("adapter", help="draft or check an adapter against an upstream checkout")
    s.add_argument("action", choices=["draft", "check"])
    s.add_argument("--source", required=True)
    s.add_argument("--from", dest="src", required=True)
    s.set_defaults(fn=cmd_adapter)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except userdata.NewerDataError as e:
        print(f"open-skill: {e}", file=sys.stderr)
        return 3
