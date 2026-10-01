"""Parallel agent sessions on one project: declared scopes, one shared Graphify graph, conflict warnings.

Session records are files in <project>/.open-skill/sessions/. Graphify writes and locks the graph itself;
open-skill only reads graphify-out/graph.json. Conflicts are warnings, never errors.
"""

import datetime as dt
import json
import os
import re
import secrets
import shutil
import subprocess
from collections import defaultdict, deque
from pathlib import Path, PurePosixPath

from . import paths, project as project_mod

STALE = dt.timedelta(hours=6)
FIELDS = {"id", "scope", "task", "started", "seen", "base"}
ID = re.compile(r"[0-9a-f]{6}")
WALK = {"calls", "indirect_call", "references", "imports", "imports_from"}
HOPS = 2
OWN = (".open-skill/", "graphify-out/")  # our own bookkeeping never counts as a change or a scope match
GRAPH = Path("graphify-out") / "graph.json"
INSTALL_FALLBACK = "uv tool install graphifyy"


class GraphifyMissing(Exception):
    pass


class GraphMissing(Exception):
    pass


class RefreshFailed(Exception):
    pass


# --- records ------------------------------------------------------------------------------------------------------

def _dir(project: Path) -> Path:
    return Path(project) / ".open-skill" / "sessions"


def _now(now=None) -> dt.datetime:
    return now or dt.datetime.now(dt.timezone.utc)


def _stamp(t: dt.datetime) -> str:
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(stamp: str) -> dt.datetime:
    return dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def _git(project: Path, *args) -> str | None:
    try:
        p = subprocess.run(["git", *args], cwd=project, capture_output=True, encoding="utf-8", errors="replace")
    except OSError:  # no git at all
        return None
    return p.stdout if p.returncode == 0 else None


def _check_scope(scope) -> list[str]:
    scope = [str(g).replace("\\", "/") for g in scope]
    if not scope:
        raise ValueError("a session needs at least one --scope glob")
    for g in scope:
        pp = PurePosixPath(g)
        if not g or pp.is_absolute() or re.match(r"^[A-Za-z]:", g) or ".." in pp.parts:
            raise ValueError(f"scope globs are relative to the project root, without '..': {g}")
    return scope


def _check_task(task: str) -> str:
    task = " ".join(str(task).splitlines()).strip()
    if not 1 <= len(task) <= 200:
        raise ValueError("a task is 1-200 characters")
    return task


def _write(project: Path, rec: dict) -> None:
    path = _dir(project) / f"{rec['id']}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read(path: Path) -> dict | None:
    """A record, or None when the file is unreadable (bad JSON, missing fields, id not its file name)."""
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rec, dict) or not FIELDS <= set(rec) or rec["id"] != path.stem:
            return None
        _parse(rec["seen"])
        return rec
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        return None


def _is_active(rec: dict, now: dt.datetime) -> bool:
    return now - _parse(rec["seen"]) <= STALE


def _all(project: Path) -> list[tuple[Path, dict | None]]:
    folder = _dir(project)
    return [(p, _read(p)) for p in sorted(folder.glob("*.json"))] if folder.is_dir() else []


def start(project, scope, task, now=None) -> dict:
    project = Path(project)
    scope, task, t = _check_scope(scope), _check_task(task), _stamp(_now(now))
    head = _git(project, "rev-parse", "--verify", "-q", "HEAD")
    folder = _dir(project)
    folder.mkdir(parents=True, exist_ok=True)
    ignore = folder.parent / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    with paths.locked(folder / ".lock"):
        sid = secrets.token_hex(3)
        while (folder / f"{sid}.json").exists():
            sid = secrets.token_hex(3)
        rec = {"id": sid, "scope": scope, "task": task, "started": t, "seen": t, "base": head.strip() if head else None}
        _write(project, rec)
    return rec


def active(project, now=None) -> list[dict]:
    now = _now(now)
    return [r for _, r in _all(Path(project)) if r and _is_active(r, now)]


def get(project, sid: str) -> dict | None:
    return _read(_dir(project) / f"{sid}.json") if ID.fullmatch(sid or "") else None


def touch(project, sid: str, now=None) -> bool:
    """Refresh last activity of an active session; False (and no change) for an unknown or stale one."""
    now = _now(now)
    if not ID.fullmatch(sid or ""):
        return False
    with paths.locked(_dir(project) / ".lock"):
        rec = get(project, sid)
        if not rec or not _is_active(rec, now):
            return False
        rec["seen"] = _stamp(now)
        _write(Path(project), rec)
    return True


def end(project, sid: str) -> None:
    path = _dir(project) / f"{sid}.json"
    if not ID.fullmatch(sid or "") or not path.exists():
        raise KeyError(sid)
    with paths.locked(_dir(project) / ".lock"):
        path.unlink(missing_ok=True)


def prune(project, now=None) -> int:
    now = _now(now)
    n = 0
    with paths.locked(_dir(project) / ".lock"):
        for path, rec in _all(Path(project)):
            if rec is None or not _is_active(rec, now):
                path.unlink(missing_ok=True)
                n += 1
    return n


def _project_files(project: Path) -> list[str]:
    return [f for f in project_mod._files(project) if not f.startswith(OWN)]


def overlaps(project, scope, exclude_id=None, now=None) -> list[tuple[str, str, str]]:
    """(session id, task, a shared glob or a file both match) for each active session whose scope overlaps scope."""
    files = _project_files(Path(project))
    out = []
    for s in active(project, now):
        if s["id"] == exclude_id:
            continue
        same = next((g for g in scope if g in s["scope"]), None)  # also for paths project._files skips (build/, ...)
        hit = same or next((f for f in files if any(project_mod._match(f, g) for g in scope)
                            and any(project_mod._match(f, g) for g in s["scope"])), None)
        if hit:
            out.append((s["id"], s["task"], hit))
    return out


def unmatched(project, scope) -> list[str]:
    files = _project_files(Path(project))
    return [g for g in scope if not any(project_mod._match(f, g) for f in files)]


# --- the shared graph ---------------------------------------------------------------------------------------------

def load_graph(project) -> dict:
    return json.loads((Path(project) / GRAPH).read_text(encoding="utf-8"))


def _inside(project: Path, rel: str) -> Path | None:
    """rel as a path under project, or None when it is absolute or escapes it (graph.json is data, not trusted)."""
    if not rel or PurePosixPath(rel).is_absolute() or re.match(r"^[A-Za-z]:", rel):
        return None
    path = (project / rel).resolve()
    return path if path.is_relative_to(project.resolve()) and path.is_file() else None


def _imported_names(project: Path, rel: str, loc: str) -> set[str]:
    """Names imported by the statement at line loc (`L<n>`) of rel, joined across a parenthesized statement."""
    path, m = _inside(project, rel), re.fullmatch(r"L(\d+)", loc or "")
    if not path or not m:
        return set()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    i = int(m.group(1)) - 1
    if not 0 <= i < len(lines):
        return set()
    stmt = lines[i]
    while "(" in stmt and ")" not in stmt and i + 1 < len(lines):
        i += 1
        stmt += " " + lines[i]
    m = re.search(r"\bimport\b(.*)", stmt.split("#")[0])
    return {n.split(" as ")[0].strip(" ()\t") for n in m.group(1).split(",")} - {""} if m else set()


def affected_files(project, graph: dict, changed, hops: int = HOPS, resolve_packages: bool = True) -> list[str]:
    """Files reaching a changed file within `hops` reverse steps over calls, references and imports."""
    return sorted(_reach(Path(project), graph, changed, hops, resolve_packages))


def _reach(project: Path, graph: dict, changed, hops=HOPS, resolve_packages=True) -> dict[str, str]:
    """{affected file: the changed file it was reached from}."""
    nodes = {n["id"]: n.get("source_file") or "" for n in graph.get("nodes", [])}
    rev = defaultdict(list)
    for link in graph.get("links", []):
        if link.get("relation") in WALK:
            rev[link["target"]].append(link["source"])
    # Graphify points `from pkg import mod` at pkg/__init__.py; resolve it to pkg/mod.py so importers are reached.
    importers = defaultdict(set)
    if resolve_packages:
        files = set(nodes.values())
        for link in graph.get("links", []):
            target = nodes.get(link.get("target"), "")
            if link.get("relation") == "imports_from" and target.endswith("__init__.py"):
                pkg = str(PurePosixPath(target).parent)
                for name in _imported_names(project, link.get("source_file", ""), link.get("source_location", "")):
                    mod = f"{name}.py" if pkg == "." else f"{pkg}/{name}.py"
                    if mod in files:
                        importers[mod].add(link["source"])
    changed = set(changed)
    origin = {nid: f for nid, f in nodes.items() if f in changed}
    queue = deque((nid, 0) for nid in origin)
    while queue:
        cur, depth = queue.popleft()
        if depth == hops:
            continue
        for nxt in [*rev[cur], *importers.get(nodes.get(cur, ""), ())]:
            if nxt not in origin:
                origin[nxt] = origin[cur]
                queue.append((nxt, depth + 1))
    out = {}
    for nid, via in origin.items():
        f = nodes.get(nid, "")
        if f and f not in changed:
            out.setdefault(f, via)
    return out


def changed_files(project, base: str | None = None):
    """(files differing from base or HEAD plus untracked files, warnings), or None when git cannot tell."""
    project = Path(project)
    if _git(project, "rev-parse", "--verify", "-q", "HEAD") is None:
        return None
    warnings = []
    if base and _git(project, "cat-file", "-e", f"{base}^{{commit}}") is None:
        warnings.append(f"session base {base} is gone; compared with HEAD")
        base = None
    # -z: paths exactly as they are; without it git quotes non-ASCII names, which then match no scope
    diff = _git(project, "diff", "--name-only", "-z", base or "HEAD")
    new = _git(project, "ls-files", "-z", "--others", "--exclude-standard")
    if diff is None or new is None:
        return None
    files = {f for f in (diff + new).split("\0") if f and not f.startswith(OWN)}
    return sorted(files), warnings


def conflicts(project, reached: dict[str, str], exclude_id=None, now=None) -> list[dict]:
    """Files (with the changed file that reaches them) that fall inside another active session's scope."""
    out = []
    for s in active(project, now):
        if s["id"] == exclude_id:
            continue
        for f, via in sorted(reached.items()):
            if any(project_mod._match(f, g) for g in s["scope"]):
                out.append({"file": f, "session": s["id"], "task": s["task"], "via": via})
    return out


def update(project, session_id=None, install_hint=INSTALL_FALLBACK, now=None) -> dict:
    """Refresh the shared graph through Graphify, then report changed and affected files and scope conflicts."""
    project = Path(project)
    if not shutil.which("graphify"):
        raise GraphifyMissing(f"graphify is not installed; install it with: {install_hint}")
    if not (project / GRAPH).is_file():
        raise GraphMissing("no graph yet; build it once with: graphify extract . --code-only")
    p = subprocess.run(["graphify", "update", "."], cwd=project, capture_output=True,
                       encoding="utf-8", errors="replace")  # Graphify locks
    if p.returncode != 0:
        raise RefreshFailed((p.stderr or p.stdout).strip())
    graph = load_graph(project)
    result = {"session": None, "graph": {"refreshed": True, "nodes": len(graph.get("nodes", [])),
                                         "edges": len(graph.get("links", []))},
              "base": None, "changed": [], "git": False, "affected": [], "conflicts": [], "others": [],
              "warnings": []}
    own = get(project, session_id) if session_id else None
    if session_id:
        if touch(project, session_id, now):
            result["session"] = session_id
        else:
            own = None
            result["warnings"].append(f"session {session_id} is unknown or stale; checked against all active sessions")
    got = changed_files(project, own["base"] if own else None)
    if got is None:
        return result
    changed, warnings = got
    result["warnings"] += warnings
    base = own["base"] if own and not warnings else None
    result.update(git=True, changed=changed, base=base or (_git(project, "rev-parse", "HEAD") or "").strip() or None)
    mine, result["others"] = _split(project, changed, own if result["session"] else None, now)
    reached = _reach(project, graph, mine)
    result["affected"] = sorted(reached)
    result["conflicts"] = conflicts(project, {**reached, **{f: f for f in mine}}, exclude_id=result["session"], now=now)
    return result


def _split(project, changed, own, now=None) -> tuple[list[str], list[dict]]:
    """(this session's changes, other sessions' own work). Sessions share one working tree, so a changed file that
    lies only in another session's scope is taken as that session's edit, not a conflict; without a session every
    change is ours."""
    if own is None:
        return list(changed), []
    others = [s for s in active(project, now) if s["id"] != own["id"]]
    mine, theirs = [], []
    for f in changed:
        owners = [s for s in others if any(project_mod._match(f, g) for g in s["scope"])]
        if owners and not any(project_mod._match(f, g) for g in own["scope"]):
            theirs += [{"file": f, "session": s["id"], "task": s["task"]} for s in owners]
        else:
            mine.append(f)
    return mine, theirs
