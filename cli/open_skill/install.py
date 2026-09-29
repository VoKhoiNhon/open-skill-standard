"""Install skills into an agent's skill folder, and record what open-skill created so it only ever removes that."""

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import __version__, agents, frontmatter, knowledge, paths, userdata

MANIFEST = "installed.json"  # in ~/.open-skill: every folder open-skill created, with the hash of each file
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")  # Agent Skills name rule; also keeps the folder inside the target


@dataclass
class Source:
    name: str
    path: Path
    kind: str  # "core" (shipped with open-skill) or "local" (a folder on disk)


def core_skills() -> dict[str, Path]:
    root = paths.data_root() / "skills"
    return {p.name: p for p in sorted(root.iterdir()) if (p / "SKILL.md").is_file()}


def resolve_source(spec: str) -> Source:
    """A folder holding SKILL.md, or the name of a core skill."""
    folder = Path(spec).expanduser()
    if (folder / "SKILL.md").is_file():
        folder, kind = folder.resolve(), "local"
    elif spec in core_skills():
        folder, kind = core_skills()[spec], "core"
    else:
        raise ValueError(f"{spec}: not a folder with a SKILL.md and not a core skill ({', '.join(core_skills())})")
    meta, _ = frontmatter.parse((folder / "SKILL.md").read_text(errors="replace"))
    name = frontmatter.text(meta, "name") or folder.name
    if not NAME.match(name):
        raise ValueError(f"{folder}: skill name {name!r} must be lowercase letters, digits and single hyphens")
    return Source(name, folder, kind)


@dataclass
class Plan:
    source: Source
    agent: str
    scope: str  # "global" or "project"
    dest: Path
    mode: str = "copy"  # or "symlink"
    action: str = "install"  # install | unchanged | refuse
    reason: str = ""


def target(agent: dict, name: str, project: Path | None = None) -> Path:
    """The folder a skill named `name` gets for this agent: under its first project folder, else its first global one."""
    if not NAME.match(name):
        raise ValueError(f"skill name {name!r} must be lowercase letters, digits and single hyphens")
    scope = "project" if project is not None else "global"
    folders = agents.folders(agent, scope, project)
    if not folders:
        raise ValueError(f"{agent['id']} has no {scope} skill folder")
    return folders[0] / name


def plan(src: Source, agent: dict, project: Path | None = None, mode: str = "copy") -> Plan:
    """Where `src` goes for this agent: its first project folder with `project`, else its first global folder."""
    scope = "project" if project is not None else "global"
    p = Plan(src, agent["id"], scope, target(agent, src.name, project), mode)
    if os.path.lexists(p.dest):
        if _same(src.path, p.dest):
            p.action, p.reason = "unchanged", f"{p.dest} already holds this skill"
        else:
            p.action, p.reason = "refuse", f"{p.dest} already holds a different skill; open-skill never overwrites it"
    return p


def _same(src: Path, dest: Path) -> bool:
    if dest.is_symlink():
        return dest.resolve() == src.resolve()
    return dest.is_dir() and _files(dest) == _files(src)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(root: Path) -> dict[str, str]:
    """Relative path -> sha256 of every file in a skill folder (version-control folders left out)."""
    return {p.relative_to(root).as_posix(): _hash(p) for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def manifest() -> list[dict]:
    f = paths.user_home() / MANIFEST
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else []


def _save(records: list[dict]) -> None:
    knowledge._prepare()  # never write over data from a newer open-skill
    userdata.atomic_write(paths.user_home() / MANIFEST, json.dumps(records, indent=1, ensure_ascii=False) + "\n")


def _copy(src: Path, dest: Path) -> None:
    """Copy into a hidden sibling first and rename, so a failed copy never leaves a half-written skill."""
    tmp = Path(tempfile.mkdtemp(dir=dest.parent, prefix=f".{dest.name}.open-skill-"))
    try:
        for rel in _files(src):
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / rel, tmp / rel)
        if os.path.lexists(dest):
            raise FileExistsError(f"{dest} appeared while installing; left untouched")
        os.replace(tmp, dest)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def apply(p: Plan) -> None:
    """Carry out an install plan and record what was created. Plans that are not installs change nothing."""
    if p.action != "install":
        return
    p.dest.parent.mkdir(parents=True, exist_ok=True)
    if p.mode == "symlink":
        os.symlink(p.source.path, p.dest, target_is_directory=True)
    else:
        _copy(p.source.path, p.dest)
    rec = {"skill": p.source.name, "agent": p.agent, "scope": p.scope, "dest": str(p.dest),
           "source": str(p.source.path), "kind": p.source.kind, "mode": p.mode, "version": __version__,
           "files": {} if p.mode == "symlink" else _files(p.dest), "installed": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    _save([r for r in manifest() if r["dest"] != rec["dest"]] + [rec])


def record_for(dest: Path) -> dict | None:
    return next((r for r in manifest() if r["dest"] == str(dest)), None)


def _ours(dest: Path, rel: str, sha: str) -> bool:
    """A recorded file still exactly as installed, reached without passing through any link."""
    path = dest / rel
    return (not dest.is_symlink() and path.is_file() and path.resolve() == dest.resolve() / rel
            and _hash(path) == sha)


def remove(dest: Path, dry_run: bool = False) -> tuple[list[str], list[str]]:
    """Delete what open-skill installed at `dest`: only recorded files whose content is unchanged, then folders
    left empty. Returns (removed, kept). Files the user changed or added stay. LookupError if not ours."""
    rec = record_for(dest)
    if rec is None:
        raise LookupError(f"{dest} was not installed by open-skill; nothing removed")
    if rec["mode"] == "symlink":
        ours = dest.is_symlink() and os.readlink(dest) == rec["source"]
        if not dry_run:
            if ours:
                dest.unlink()
            _save([r for r in manifest() if r["dest"] != str(dest)])
        return ([rec["skill"]], []) if ours else ([], [rec["skill"]])
    removed = [rel for rel, sha in rec["files"].items() if _ours(dest, rel, sha)]
    kept = sorted(set(_files(dest)) - set(removed)) if dest.is_dir() else []
    if dry_run:
        return removed, kept
    for rel in removed:
        (dest / rel).unlink()
    for d in sorted((p for p in dest.rglob("*") if p.is_dir() and not p.is_symlink()), key=lambda p: -len(p.parts)):
        if not any(d.iterdir()):
            d.rmdir()
    if dest.is_dir() and not any(dest.iterdir()):
        dest.rmdir()
    _save([r for r in manifest() if r["dest"] != str(dest)])
    return removed, kept


def _replace(dest: Path, new: Path) -> None:
    """Swap a verified, unchanged install for a fresh copy; the old one is restored if the copy fails."""
    old = Path(tempfile.mkdtemp(dir=dest.parent, prefix=f".{dest.name}.open-skill-old-"))
    old.rmdir()
    os.replace(dest, old)
    try:
        _copy(new, dest)
    except BaseException:
        os.replace(old, dest)
        raise
    shutil.rmtree(old)  # only files open-skill recorded, checked unchanged just before


def update(agent: str | None = None, dry_run: bool = False) -> list[str]:
    """Reinstall core skills open-skill installed, pinned to this CLI's version. Installs the user changed are skipped."""
    core, out, records = core_skills(), [], manifest()
    for rec in records:
        if agent and rec["agent"] != agent:
            continue
        dest, name, who = Path(rec["dest"]), rec["skill"], f"{rec['skill']} for {rec['agent']}"
        if rec["kind"] != "core" or name not in core:
            out.append(f"skipped {dest}: local skill; install it again from its folder to update")
            continue
        new = core[name]
        if rec["mode"] == "symlink":
            if not (dest.is_symlink() and os.readlink(dest) == rec["source"]):
                out.append(f"skipped {dest}: you changed it since install; left as is")
                continue
            current = rec["source"] == str(new)
        else:
            if dest.is_symlink() or not dest.is_dir() or _files(dest) != rec["files"]:
                out.append(f"skipped {dest}: you changed it since install; left as is")
                continue
            current = _files(dest) == _files(new)
        if current:
            out.append(f"up to date: {who} ({__version__}) → {dest}")
        else:
            out.append(f"{'would update' if dry_run else 'updated'} {who} {rec.get('version')} → {__version__}: {dest}")
        if dry_run:
            continue
        if not current and rec["mode"] == "symlink":
            dest.unlink()
            os.symlink(new, dest, target_is_directory=True)
        elif not current:
            _replace(dest, new)
        rec.update(source=str(new), version=__version__, files={} if rec["mode"] == "symlink" else _files(dest))
    if not dry_run and records:
        _save(records)
    return out
