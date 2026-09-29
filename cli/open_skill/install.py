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
    name = str(meta.get("name") or folder.name)
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


def plan(src: Source, agent: dict, project: Path | None = None, mode: str = "copy") -> Plan:
    """Where `src` goes for this agent: its first project folder with `project`, else its first global folder."""
    scope = "project" if project is not None else "global"
    targets = agents.folders(agent, scope, project)
    if not targets:
        raise ValueError(f"{agent['id']} has no {scope} skill folder")
    return Plan(src, agent["id"], scope, targets[0] / src.name, mode)


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
    _copy(p.source.path, p.dest)
    rec = {"skill": p.source.name, "agent": p.agent, "scope": p.scope, "dest": str(p.dest),
           "source": str(p.source.path), "kind": p.source.kind, "mode": p.mode, "version": __version__,
           "files": _files(p.dest), "installed": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    _save([r for r in manifest() if r["dest"] != rec["dest"]] + [rec])
