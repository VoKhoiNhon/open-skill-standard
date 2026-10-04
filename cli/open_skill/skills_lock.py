"""The `skills-lock.json` that `npx skills` (vercel-labs/skills) writes at a project root.

Each entry names a skill, where it came from and a hash of its folder as installed. Comparing that hash with the
folder today tells a skill edited since install from one that is as installed. Files are only read.
Format: https://github.com/vercel-labs/skills/blob/7533583f24a9a9be6fd5f783912f55c15a08b31e/src/local-lock.ts
"""

import hashlib
import json
import os
import unicodedata
from pathlib import Path

LOCK_FILE = "skills-lock.json"
VERSION = 1

# The lock hash sorts files with JavaScript's localeCompare, which follows Unicode collation rather than code points:
# punctuation before digits before letters, letters compared without case first and lowercase ahead of uppercase on a
# tie, accents after the letter they mark. This is that order for ASCII; other characters follow it by code point.
_ORDER = "\t\n\r _-,;:!?.'\"()[]{}@*/\\&#%`^+<=>|~$0123456789abcdefghijklmnopqrstuvwxyz"
_PRIMARY = {c: i for i, c in enumerate(_ORDER)}


def _collation_key(s: str):
    primary, secondary, tertiary = [], [], []
    for c in unicodedata.normalize("NFD", s):
        if unicodedata.combining(c):
            secondary.append(ord(c))
            continue
        low = c.lower()
        primary.append(_PRIMARY.get(low, len(_ORDER) + ord(low)))
        secondary.append(0)
        tertiary.append(c != low)
    return primary, secondary, tertiary


def folder_hash(folder: Path) -> str:
    """The lock's `computedHash`: SHA-256 over each file's /-separated relative path and bytes, in collation order,
    skipping `.git` and `node_modules` folders; links are neither files nor folders to it, so they are skipped."""
    files = []
    for d, dirs, names in os.walk(folder):
        dirs[:] = [x for x in dirs if x not in (".git", "node_modules") and not os.path.islink(os.path.join(d, x))]
        for n in names:
            p = Path(d, n)
            if p.is_file() and not p.is_symlink():
                files.append((p.relative_to(folder).as_posix(), p))
    h = hashlib.sha256()
    for rel, p in sorted(files, key=lambda f: _collation_key(f[0])):
        h.update(rel.encode("utf-8"))
        h.update(p.read_bytes())
    return h.hexdigest()


def read(project: Path) -> dict[str, dict] | None:
    """Skill name -> lock entry, or None when the project has no readable lock (npx skills ignores a broken one too)."""
    try:
        doc = json.loads((Path(project) / LOCK_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("version"), int) or doc["version"] < VERSION:
        return None
    skills = doc.get("skills")
    if not isinstance(skills, dict):
        return None
    return {k: v for k, v in skills.items() if isinstance(v, dict)}


def check(project: Path, skill_dirs) -> dict[str, list[str]] | None:
    """Compare each locked skill with its copies in the project's skill folders (relative paths such as
    `.agents/skills`), or None without a lock. Returns {"ok", "changed", "missing"} lists of skill names; a skill
    counts as changed when any copy no longer has the hash it was installed with."""
    lock = read(project)
    if lock is None:
        return None
    out: dict[str, list[str]] = {"ok": [], "changed": [], "missing": []}
    for name, entry in sorted(lock.items()):
        if not name or name in (".", "..") or "/" in name or "\\" in name:  # a name, never a path out of the folder
            continue
        found = [Path(project, d, name) for d in sorted(set(skill_dirs))
                 if Path(project, d, name, "SKILL.md").is_file()]
        if not found:
            out["missing"].append(name)
        elif any(folder_hash(f) != entry.get("computedHash") for f in found):
            out["changed"].append(name)
        else:
            out["ok"].append(name)
    return out
