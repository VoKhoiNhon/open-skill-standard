"""The `skills-lock.json` that `npx skills` (vercel-labs/skills) writes at a project root.

Each entry names a skill, where it came from and a hash of its folder as installed. Comparing that hash with the
folder today tells a skill edited since install from one that is as installed. Files are only read.
Format: https://github.com/vercel-labs/skills/blob/7533583f24a9a9be6fd5f783912f55c15a08b31e/src/local-lock.ts
"""

import hashlib
import json
import os
from pathlib import Path

LOCK_FILE = "skills-lock.json"
VERSION = 1
SKIPPED_DIRS = (".git", "node_modules", "__pycache__", "__pypackages__")

# The lock hash sorts files with JavaScript's localeCompare, which follows Unicode collation rather than code points:
# punctuation before digits before letters, letters compared without case first and lowercase ahead of uppercase on a
# tie. This is that order for ASCII. Accented, CJK and emoji names need the full collation tables, which Python lacks,
# so a folder with such a file name is reported as unchecked rather than given a hash that may not match.
_ORDER = "\t\n\r _-,;:!?.'\"()[]{}@*/\\&#%`^+<=>|~$0123456789abcdefghijklmnopqrstuvwxyz"
_PRIMARY = {c: i for i, c in enumerate(_ORDER)}


def _collation_key(s: str):
    """localeCompare order for printable ASCII strings."""
    return [_PRIMARY.get(c.lower(), len(_ORDER) + ord(c)) for c in s], [c.isupper() for c in s]


def folder_hash(folder: Path) -> str | None:
    """The lock's `computedHash`: SHA-256 over each file's /-separated relative path and bytes, in collation order,
    skipping `.git` and `node_modules` folders; links are neither files nor folders to it, so they are skipped.
    `__pycache__` and `__pypackages__` are skipped too: npx skills never copies them, so they appear only when a
    skill's scripts run, which is not an edit.
    None when a file name is not ASCII (its order cannot be reproduced) or a file cannot be read."""
    files = []
    for d, dirs, names in os.walk(folder):
        dirs[:] = [x for x in dirs if x not in SKIPPED_DIRS and not os.path.islink(os.path.join(d, x))]
        for n in names:
            p = Path(d, n)
            if p.is_file() and not p.is_symlink():
                files.append((p.relative_to(folder).as_posix(), p))
    if not all(rel.isascii() for rel, _ in files):
        return None
    h = hashlib.sha256()
    try:
        for rel, p in sorted(files, key=lambda f: _collation_key(f[0])):
            h.update(rel.encode("utf-8"))
            h.update(p.read_bytes())
    except OSError:  # unreadable or gone mid-walk: no verdict rather than a crash
        return None
    return h.hexdigest()


def find(start: Path) -> Path | None:
    """The folder whose lock applies to `start`: `start` itself, or the nearest parent up to the repository root (the
    nearest folder with `.git`), where npx skills writes it when run there. Outside a repository only `start` counts."""
    start = Path(start).resolve()
    root = next((d for d in [start, *start.parents] if (d / ".git").exists()), None)
    dirs = [start]
    if root is not None and root != start:
        dirs += start.parents[: start.parents.index(root) + 1]
    return next((d for d in dirs if (d / LOCK_FILE).is_file()), None)


def read(project: Path) -> dict[str, dict] | None:
    """Skill name -> lock entry, or None when the project has no readable lock (npx skills ignores a broken one too)."""
    try:
        doc = json.loads((Path(project) / LOCK_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return None
    version = doc.get("version") if isinstance(doc, dict) else None
    if not isinstance(version, int) or isinstance(version, bool) or version < VERSION:
        return None
    skills = doc.get("skills")
    if not isinstance(skills, dict):
        return None
    return {k: v for k, v in skills.items() if isinstance(v, dict)}


def check(project: Path, skill_dirs) -> dict[str, list[str]] | None:
    """Compare each locked skill with its copies in the project's skill folders (relative paths such as
    `.agents/skills`), or None without a lock. Returns {"ok", "changed", "missing", "unchecked"} lists of skill
    names; a skill counts as changed when any copy no longer has the locked hash, and as unchecked when a copy cannot
    be hashed the way the lock was. npx skills hashes the source folder, then copies it without `metadata.json` and
    with links made into files, so such a skill differs from its lock without any edit: "changed" means "differs"."""
    lock = read(project)
    if lock is None:
        return None
    out: dict[str, list[str]] = {"ok": [], "changed": [], "missing": [], "unchecked": []}
    for name, entry in sorted(lock.items()):
        if not name or name in (".", "..") or any(c in name for c in "/\\:"):  # a name, never a path or a drive
            continue
        found = [Path(project, d, name) for d in sorted(set(skill_dirs))
                 if Path(project, d, name, "SKILL.md").is_file()]
        hashes = [folder_hash(f) for f in found]
        if not found:
            out["missing"].append(name)
        elif None in hashes:
            out["unchecked"].append(name)
        elif any(h != entry.get("computedHash") for h in hashes):
            out["changed"].append(name)
        else:
            out["ok"].append(name)
    return out
