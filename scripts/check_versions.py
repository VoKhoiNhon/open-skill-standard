"""Fail when the version differs between files, or skills are pinned to another release."""

import json
import re
import sys
from pathlib import Path

GIT_URL = "git+https://github.com/VoKhoiNhon/open-skill-standard"


def versions(root: Path) -> dict[str, str]:
    found = {
        "pyproject.toml": re.search(r'(?m)^version = "([^"]+)"', (root / "pyproject.toml").read_text()).group(1),
        "cli/open_skill/__init__.py": re.search(r'__version__ = "([^"]+)"', (root / "cli/open_skill/__init__.py").read_text()).group(1),
        ".claude-plugin/plugin.json": json.loads((root / ".claude-plugin/plugin.json").read_text())["version"],
        "registry/adapters/open-skill.yaml": re.search(r"(?m)^tested_version: (.+)$", (root / "registry/adapters/open-skill.yaml").read_text()).group(1).strip(),
    }
    for p in sorted(root.glob("skills/*/SKILL.md")):
        for pin in re.findall(re.escape(GIT_URL) + r"@v([\w.\-]+)", p.read_text()):
            found[f"{p.relative_to(root)} pin"] = pin
    return found


def main(root: str = ".") -> int:
    found = versions(Path(root))
    distinct = set(found.values())
    if len(distinct) == 1:
        print(f"version {distinct.pop()} everywhere ({len(found)} places)")
        return 0
    for where, v in found.items():
        print(f"{v:10} {where}")
    print("versions disagree; run scripts/bump_version.py <version>")
    return 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
