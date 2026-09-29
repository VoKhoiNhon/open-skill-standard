"""Cheap project inspection: framework markers, artifacts, languages, role signals. Never reads file contents."""

import fnmatch
import os
from collections import Counter
from pathlib import Path

SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", "target", ".tox"}
MAX_FILES = 5000


def _files(root: Path) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        rel = os.path.relpath(dirpath, root)
        for f in filenames:
            out.append(f if rel == "." else f"{rel}/{f}".replace(os.sep, "/"))
            if len(out) >= MAX_FILES:
                return out
    return out


def _match(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or (pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]))


def inspect(root: Path, taxonomy: dict, roles: dict) -> dict:
    root = Path(root)
    files = _files(root) if root.is_dir() else []
    native = next(
        (m["framework"] for m in taxonomy.get("native_markers", []) if any((root / p).exists() for p in m["paths"])),
        None,
    )
    markers = sorted(
        p for m in taxonomy.get("native_markers", []) for p in m["paths"] if (root / p).exists()
    ) + sorted(p for ps in taxonomy.get("tool_markers", {}).values() for p in ps if (root / p).exists())
    artifacts = sorted(a for a, globs in taxonomy["artifacts"].items() if any(_match(f, g) for f in files for g in globs))
    signals = {}
    for rid, r in roles.items():
        hits = sum(1 for g in r.get("signals", []) if any(_match(f, g) for f in files))
        if hits:
            signals[rid] = hits
    langs = Counter(Path(f).suffix for f in files if Path(f).suffix)
    return {
        "path": str(root.resolve()),
        "native": native,
        "markers": markers,
        "artifacts": artifacts,
        "codegraph": any((root / p).exists() for p in taxonomy.get("tool_markers", {}).get("codegraph", [])),
        "languages": dict(langs.most_common(10)),
        "role_signals": signals,
    }
