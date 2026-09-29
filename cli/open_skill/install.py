"""Install skills into an agent's skill folder, and record what open-skill created so it only ever removes that."""

import re
from dataclasses import dataclass
from pathlib import Path

from . import agents, frontmatter, paths

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
