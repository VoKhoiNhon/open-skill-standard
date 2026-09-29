"""Fail unless a built wheel carries the registry, spec, skills, evals and modules the CLI needs at run time.

Usage: python scripts/check_wheel.py dist/<wheel>.whl  (run from a checkout: every tracked data file must be inside)
"""

import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ("registry", "spec", "skills", "evals")  # force-included under open_skill/_data/ (pyproject.toml)


def required(root: Path) -> list[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}
    files = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True, check=True, env=env).stdout
    out = []
    for f in filter(None, files.split("\0")):
        if f.startswith("cli/open_skill/") and f.endswith(".py"):
            out.append("open_skill/" + f.removeprefix("cli/open_skill/"))
        elif f.split("/")[0] in DATA:
            out.append("open_skill/_data/" + f)
    return sorted(out)


def missing(wheel: str, root: Path = ROOT) -> list[str]:
    names = set(zipfile.ZipFile(wheel).namelist())
    return [r for r in required(root) if r not in names]


if __name__ == "__main__":
    gaps = missing(sys.argv[1])
    for g in gaps:
        print(f"missing from wheel: {g}")
    sys.exit(1 if gaps else 0)
