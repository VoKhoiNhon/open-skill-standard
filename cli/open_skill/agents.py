"""Coding agents that load Agent Skills, and the folders each one reads (registry/agents)."""

import os
from pathlib import Path


def expand(agent: dict, path: str) -> Path:
    """`~` is the home folder; a relocation env var, when set, replaces its path prefix (for example CODEX_HOME)."""
    for r in agent.get("relocate", []):
        value = os.environ.get(r["var"], "").strip()
        prefix = r["replaces"]
        if value and (path == prefix or path.startswith(prefix + "/")):
            path = value.rstrip("/") + path[len(prefix):]
            break
    return Path(path).expanduser()


def folders(agent: dict, scope: str, project: Path | None = None) -> list[Path]:
    """Skill folders for scope "global" or "project", install target first. Project folders need a project; an agent
    that walks up also reads them in every parent folder up to the repository root (the nearest folder with `.git`)."""
    if scope == "global":
        return [expand(agent, f["path"]) for f in agent.get("global", [])]
    if project is None:
        return []
    start = Path(project).resolve()
    dirs = [start]
    if agent.get("walk_up"):
        root = next((d for d in [start, *start.parents] if (d / ".git").exists()), None)
        if root is not None and root != start:
            dirs += start.parents[: start.parents.index(root) + 1]
    return [d / f["path"] for d in dirs for f in agent.get("project", [])]


def detected(agent: dict) -> bool:
    """Installed on this machine: any detect path exists (after relocation)."""
    return any(expand(agent, d["path"]).exists() for d in agent.get("detect", []))
