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
        p = subprocess.run(["git", *args], cwd=project, capture_output=True, text=True)
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
    except (OSError, ValueError, TypeError, KeyError):
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
