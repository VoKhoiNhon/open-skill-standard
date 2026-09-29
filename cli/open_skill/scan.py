"""Find the skills actually installed on this machine and map them to registry ids."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import agents, frontmatter

DEFAULT_AGENT = "claude-code"  # detect rules without an `agent`, and skills built into Claude Code

# Generic locations searched for skills no adapter rule claims: every agent's folders and Claude Code plugins.
GENERIC = [
    "{skills}/*/SKILL.md",
    "~/.claude/plugins/cache/*/*/*/skills/*/SKILL.md",
    "{project_skills}/*/SKILL.md",
]


@dataclass
class Installed:
    id: str
    invoke: str
    path: str
    description: str
    inferred: bool
    agent: str = DEFAULT_AGENT  # the agent `invoke` is valid for
    agents: dict[str, str] = field(default_factory=dict)  # every agent that sees the skill -> name it invokes


def _expand(pattern: str, project: Path | None, agent: dict | None = None) -> str | None:
    if "{project}" in pattern:
        if project is None:
            return None
        pattern = pattern.replace("{project}", str(Path(project).resolve()))
    return str(agents.expand(agent or {}, pattern)) if pattern.startswith("~") else pattern


def _regex(pattern: str) -> re.Pattern:
    out = re.escape(pattern).replace(r"\{name\}", "(?P<name>[^/]+)").replace(r"\*", "[^/]*")
    return re.compile(f"^{out}$")


def _glob(pattern: str) -> list[Path]:
    p = Path(pattern.replace("{name}", "*"))
    anchor = Path(p.anchor)
    return sorted(anchor.glob(str(p.relative_to(anchor))))


def _latest_versions(paths: list[Path]) -> list[Path]:
    """Keep only the newest plugin version when a cache holds several (…/<plugin>/<version>/skills/…)."""
    best: dict[tuple, Path] = {}
    for p in paths:
        parts = p.parts
        if "cache" in parts and "skills" in parts:
            i = parts.index("skills")
            key = parts[: i - 1] + parts[i:]
            if key not in best or parts[i - 1] > best[key].parts[i - 1]:
                best[key] = p
        else:
            best[(p,)] = p
    return sorted(best.values())


def _describe(path: Path) -> tuple[str, str]:
    meta, _ = frontmatter.parse(path.read_text(errors="replace"))
    return str(meta.get("name") or path.parent.name), str(meta.get("description") or "")


def _targets(pattern: str, project: Path | None, reg, agent: str) -> list[tuple[str, list[str]]]:
    """(glob, agents that read it). `{skills}` and `{project_skills}` fan out over every agent's skill folders;
    a folder several agents share is globbed once, its owners (the agents listing it first) ahead of the rest."""
    for placeholder, scope in (("{skills}", "global"), ("{project_skills}", "project")):
        if pattern.startswith(placeholder):
            dirs: dict[str, list[tuple[int, str]]] = {}
            for aid, a in reg.agents.items():
                for rank, d in enumerate(agents.folders(a, scope, project)):
                    dirs.setdefault(str(d), []).append((rank, aid))
            return [(d + pattern[len(placeholder):], [aid for _, aid in sorted(ids)]) for d, ids in dirs.items()]
    pat = _expand(pattern, project, reg.agents.get(agent))
    return [(pat, [agent])] if pat else []


def _add(found: dict, key: str, item: Installed, seen_by: list[str]) -> None:
    """One entry per skill; another agent seeing it only adds that agent's invocation."""
    if key not in found:
        item.agent, item.agents = seen_by[0], {}
        found[key] = item
    for aid in seen_by:
        found[key].agents.setdefault(aid, item.invoke)


def scan(reg, project: Path | None = None, agent: str | None = None) -> list[Installed]:
    """Installed skills; with `agent`, only those that agent sees, named as it invokes them."""
    found: dict[str, Installed] = {}  # registry id (or invocation, for harvested skills) -> entry
    claimed: set[Path] = set()
    for src, adapter in reg.adapters.items():
        known = {s["name"] for s in adapter.get("skills", [])}
        for rule in adapter.get("detect", []):
            # A rule may claim skills the adapter does not list only if its path is specific
            # to this source (source name in the path, or a prefix like "speckit-{name}").
            specific = f"/{src}/" in rule["glob"] or not re.search(r"/\{name\}(/|$)", rule["glob"])
            for pat, seen_by in _targets(rule["glob"], project, reg, rule.get("agent", DEFAULT_AGENT)):
                rx = _regex(pat)
                for path in _latest_versions(_glob(pat)):
                    m = rx.match(str(path))
                    if not m:
                        continue
                    name = m.group("name")
                    if name not in known and not specific:
                        continue
                    sid = f"{src}/{name}"
                    claimed.add(path.resolve())
                    inv = rule["invoke"].format(name=name)
                    # The first rule that finds a skill wins its path and, per agent, its invocation.
                    _add(found, sid, Installed(sid, inv, str(path), _describe(path)[1], name not in known), seen_by)
    for src, adapter in reg.adapters.items():
        env = adapter.get("available_env")
        if env and os.environ.get(env):
            for s in adapter.get("skills", []):
                sid, inv = f"{src}/{s['name']}", s.get("invoke", s["name"])
                _add(found, sid, Installed(sid, inv, f"builtin:{env}", s.get("description", ""), False), [DEFAULT_AGENT])
    taken = {(a, inv) for i in found.values() for a, inv in i.agents.items()}
    for pattern in GENERIC:
        for pat, seen_by in _targets(pattern, project, reg, DEFAULT_AGENT):
            for path in _latest_versions(_glob(pat)):
                if path.resolve() in claimed:
                    continue
                name, desc = _describe(path)
                parts = path.parts
                inv = f"{parts[parts.index('skills') - 2]}:{name}" if "cache" in parts else name
                free = [a for a in seen_by if (a, inv) not in taken]
                if free:
                    _add(found, inv, Installed(f"harvested/{name}", inv, str(path), desc, True), free)
                    taken |= {(a, inv) for a in free}
    items = list(found.values())
    if agent:
        items = [i for i in items if agent in i.agents]
        for i in items:
            i.agent, i.invoke = agent, i.agents[agent]
    return sorted(items, key=lambda i: i.invoke)
