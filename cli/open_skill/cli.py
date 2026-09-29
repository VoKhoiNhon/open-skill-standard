import argparse
import json
import sys
from pathlib import Path

import yaml

from . import __version__, frontmatter, generate, index, knowledge, lint, paths, registry, route, scan, userdata


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
    targets = args.paths or [str(paths.data_root() / "skills")]
    findings = lint.lint_paths(targets)
    for f in findings:
        print(f"{f.path}: [{f.rule}] {f.message} ({f.source})")
    print(f"{len(findings)} finding(s)")
    return 1 if findings else 0


def cmd_scan(args):
    reg = _registry(args)
    if args.memory:
        print(f"imported {knowledge.import_agent_memory()} memory file(s)")
        return 0
    items = scan.scan(reg, Path(args.project) if args.project else None)
    if args.json:
        _print([i.__dict__ for i in items])
    else:
        for i in items:
            print(f"{i.invoke:45} {i.id}{'  (inferred)' if i.inferred else ''}")
        print(f"{len(items)} skill(s)")
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
    for sid, score in index.search(index.build_index(reg, installed), args.query, args.limit):
        print(f"{score:7.2f}  {sid}{'' if sid in have else '  (not installed)'}")
    return 0


def _explain(r) -> str:
    lines = [f"route {r['route_id']}  role={r['role']}  size={r['size']}  target={r['target_phase']}",
             f"project native={r['project']['native']} artifacts={r['project']['artifacts']}",
             f"model profile={r['model']['profile']} ({r['model']['matched_by']}) effort={r['model']['effort']}"]
    if r["advice"]:
        lines.append(f"advice: {r['advice']}")
    for i, s in enumerate(r["chain"], 1):
        lines.append(f"{i}. [{s['phase']}] {s['invoke']}  score={s['score']}  — {s['why']}")
        if s.get("ask"):
            lines.append(f"   close call on the main step, ask the user: {s['ask']}")
        elif s.get("runner_up"):
            lines.append(f"   runner-up: {s['runner_up']}")
    for m in r["missing"]:
        lines.append(f"missing: {m['id']} ({m['reason']}) → {m['install']}")
    for k in r["knowledge"]:
        lines.append(f"knowledge [{k['type']}]: {k['text']}")
    for a in r["model"]["addenda"]:
        lines.append(f"model note: {a}")
    return "\n".join(lines)


def cmd_route(args):
    reg = _registry(args)
    proj = Path(args.project or ".")
    installed = scan.scan(reg, proj)
    r = route.route(args.task, proj, reg, installed, role=args.role, size=args.size, model=args.model,
                    record=not args.no_record)
    _print(_explain(r) if args.explain else r, as_json=not args.explain)
    return 0


def cmd_graph(args):
    reg = _registry(args)
    if args.format == "json":
        _print(index.graph_json(reg, scan.scan(reg)))
    else:
        print(index.graph_mermaid(reg), end="")
    return 0


def cmd_doctor(args):
    reg = _registry(args)
    installed = scan.scan(reg, Path(args.project) if args.project else None)
    by_src: dict[str, int] = {}
    for i in installed:
        by_src[i.id.split("/")[0]] = by_src.get(i.id.split("/")[0], 0) + 1
    print(f"open-skill {__version__}  registry={paths.data_root()}  home={knowledge.home()}")
    for src, a in sorted(reg.adapters.items()):
        n = by_src.get(src, 0)
        hint = "" if n else f"  → {next(iter((a.get('install') or {}).values()), 'see ' + a.get('upstream', ''))}"
        print(f"  {'✓' if n else '·'} {src:22} {n:3} installed / {len(a['skills'])} described{hint}")
    print(f"  harvested (no manifest): {by_src.get('harvested', 0)}")
    names: dict[str, list[str]] = {}
    for i in installed:
        names.setdefault(i.invoke.split(":")[-1], []).append(i.invoke)
    dupes = {k: v for k, v in names.items() if len(v) > 1}
    for k, v in dupes.items():
        print(f"  ! same skill name from several sources: {', '.join(v)}")
    if not (knowledge.home() / "profile.yaml").exists():
        print("  · no profile yet → open-skill init")
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
    reg = _registry(args)
    roles = list(knowledge.load_profile().get("roles", {}))
    if not roles:
        print("no roles in your profile yet; run: open-skill init --role <role>")
        return 1
    seeds = {rid: r.get("seeds", []) for rid, r in reg.roles.items()}
    actions = knowledge.sync_seeds(roles, seeds, dry_run=args.dry_run)
    print("\n".join(actions) if actions else "starter knowledge is up to date")
    return 0


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
    s = sub.add_parser("lint", help="lint SKILL.md files")
    s.add_argument("paths", nargs="*")
    s.set_defaults(fn=cmd_lint)
    s = sub.add_parser("scan", help="list installed skills")
    s.add_argument("--project")
    s.add_argument("--json", action="store_true")
    s.add_argument("--memory", action="store_true", help="import Claude Code memory files into knowledge")
    s.set_defaults(fn=cmd_scan)
    s = sub.add_parser("build", help="regenerate playbooks, schemas and dist/")
    s.add_argument("--root")
    s.add_argument("--check", action="store_true", help="exit 1 if generated files are stale")
    s.set_defaults(fn=cmd_build)
    s = sub.add_parser("search", help="full-text search over skills")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--project")
    s.set_defaults(fn=cmd_search)
    s = sub.add_parser("route", help="choose and order skills for a task")
    s.add_argument("task")
    s.add_argument("--project")
    s.add_argument("--role")
    s.add_argument("--size", choices=["small", "medium", "large"])
    s.add_argument("--model")
    s.add_argument("--explain", action="store_true")
    s.add_argument("--no-record", action="store_true")
    s.set_defaults(fn=cmd_route)
    s = sub.add_parser("graph", help="export the skill graph")
    s.add_argument("--format", choices=["mermaid", "json"], default="mermaid")
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
    s.add_argument("action", choices=["sync"])
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_seeds)
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
