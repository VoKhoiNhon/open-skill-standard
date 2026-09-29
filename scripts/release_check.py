"""Before tagging: the version is bumped everywhere, the CHANGELOG has a dated section and the compare links point at it.

Usage: python scripts/release_check.py X.Y.Z [--root .]
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from changelog import section  # noqa: E402
from check_versions import versions  # noqa: E402


def changelog_problems(text: str, v: str) -> list[str]:
    try:
        body = section(text, v)
    except KeyError:
        return [f"CHANGELOG has no section for {v}; move [Unreleased] into ## [{v}] - YYYY-MM-DD"]
    out = []
    if "## [Unreleased]" in text and re.search(r"(?m)^- ", section(text, "Unreleased")):
        out.append(f"entries left under [Unreleased]; move them into [{v}]")
    if not re.search(rf"(?m)^## \[{re.escape(v)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", text):
        out.append(f"CHANGELOG section for {v} has no date: ## [{v}] - YYYY-MM-DD")
    if not body.strip():
        out.append(f"CHANGELOG section for {v} is empty")
    if not re.search(rf"(?m)^\[Unreleased\]: \S+/compare/v{re.escape(v)}\.\.\.HEAD$", text):
        out.append(f"[Unreleased] compare link must end in /compare/v{v}...HEAD")
    older = re.findall(r"(?m)^## \[(\d+\.\d+\.\d+)\]", text.split(f"## [{v}]", 1)[1])
    prev = older[0] if older else None
    want = f"/compare/v{prev}...v{v}" if prev else f"/releases/tag/v{v}"
    if not re.search(rf"(?m)^\[{re.escape(v)}\]: \S+{re.escape(want)}$", text):
        out.append(f"[{v}]: link missing or wrong; expected ...{want}")
    return out


def problems(root: Path, v: str) -> list[str]:
    out = [f"version not bumped: {where} is {found}" for where, found in versions(root).items() if found != v]
    return out + changelog_problems((root / "CHANGELOG.md").read_text(), v)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    v = args.version.removeprefix("release/").removeprefix("v")
    found = problems(Path(args.root), v)
    for p in found:
        print(f"::error::{p}" if "GITHUB_ACTIONS" in os.environ else p)
    if not found:
        print(f"ready to tag v{v}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
