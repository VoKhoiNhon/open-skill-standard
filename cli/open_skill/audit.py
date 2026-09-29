"""Heuristic security review of skill folders: SKILL.md, references, scripts and assets.

It flags text a person should read before trusting a skill. A clean report means no rule matched,
not that the skill is safe. Files are only read as text; nothing is run or changed.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

DISCLAIMER = "heuristic review: every finding needs a human look, and a clean report does not mean a skill is safe"
SEVERITIES = ("high", "medium", "low")


@dataclass
class Finding:
    severity: str
    rule: str
    file: str
    line: int
    excerpt: str
    source: str
    message: str


@dataclass
class Rule:
    id: str
    severity: str
    pattern: re.Pattern | None  # None for rules checked per file rather than per line
    message: str
    source: str


RULES: dict[str, Rule] = {}


def rule(id: str, severity: str, pattern: str | None, message: str, source: str) -> None:
    """Register a rule; every rule cites the public guidance it comes from."""
    assert severity in SEVERITIES and id not in RULES, id
    RULES[id] = Rule(id, severity, re.compile(pattern) if pattern else None, message, source)


def _excerpt(line: str, limit: int = 160) -> str:
    # Escape control and invisible characters so an excerpt cannot hide text or drive the terminal.
    s = "".join(c if c.isprintable() else (f"\\x{ord(c):02x}" if ord(c) < 256 else f"\\u{ord(c):04x}")
                for c in line.strip())
    return s if len(s) <= limit else s[: limit - 3] + "..."


def audit_text(text: str, file: str = "<text>") -> list[Finding]:
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        for r in RULES.values():
            if r.pattern and r.pattern.search(line):
                out.append(Finding(r.severity, r.id, file, n, _excerpt(line), r.source, r.message))
    return out


def _files(root: Path):
    """Every file under root, links included but never followed, so a skill cannot point the audit elsewhere."""
    if not root.is_dir() or root.is_symlink():
        yield root
        return
    for d, dirs, names in os.walk(root):  # followlinks=False: linked folders are listed, not entered
        dirs[:] = sorted(x for x in dirs if x != ".git")
        yield from (Path(d, x) for x in sorted(names + [x for x in dirs if os.path.islink(os.path.join(d, x))]))


CWE_LINK = "https://cwe.mitre.org/data/definitions/59.html"
rule("link-outside-skill", "high", None,
     "a symbolic link points outside the skill folder; following it could read or run files the skill does not ship",
     CWE_LINK)

ANTHROPIC_SKILLS = "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#security-considerations"
rule("native-executable", "medium", None,
     "a compiled program ships with the skill; it cannot be reviewed as text, so only run it from a source you trust",
     ANTHROPIC_SKILLS)
NATIVE = (b"\x7fELF", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe",
          b"\xca\xfe\xba\xbe", b"MZ")  # ELF, Mach-O (32/64-bit, both byte orders, universal), Windows PE


def _flag(rule_id: str, path: Path, excerpt: str) -> Finding:
    r = RULES[rule_id]
    return Finding(r.severity, r.id, str(path), 0, _excerpt(excerpt), r.source, r.message)


def audit_file(path: Path, root: Path | None = None) -> list[Finding]:
    root = root or path.parent
    if path.is_symlink():  # never read through a link; a link inside the skill is audited at its target
        target = Path(os.path.realpath(path))
        inside = target.is_relative_to(Path(os.path.realpath(root)))
        return [] if inside else [_flag("link-outside-skill", path, f"-> {os.readlink(path)}")]
    data = path.read_bytes()
    if b"\0" in data[:8192]:  # binary: images and fonts are normal, programs deserve a look
        return [_flag("native-executable", path, data[:4].hex())] if data.startswith(NATIVE) else []
    return audit_text(data.decode("utf-8", errors="replace"), str(path))


def audit_paths(paths) -> list[Finding]:
    """Audit skill folders or single files; findings sorted most severe first."""
    out = []
    for p in paths:
        p = Path(os.path.realpath(p))  # a path the user names (often an installed link) is audited at its target
        out += [f for file in _files(p) for f in audit_file(file, p if p.is_dir() else p.parent)]
    return sorted(out, key=lambda f: (SEVERITIES.index(f.severity), f.file, f.line))
