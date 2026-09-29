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
    """Skill folders for scope "global" or "project", install target first. Project folders need a project."""
    if scope == "global":
        return [expand(agent, f["path"]) for f in agent.get("global", [])]
    if project is None:
        return []
    return [Path(project).resolve() / f["path"] for f in agent.get("project", [])]
