"""Fail when the version differs between files, or skills are pinned to another release."""

import re
import sys
from pathlib import Path

GIT_URL = "git+https://github.com/VoKhoiNhon/open-skill-standard"


def _field(pattern: str, path: Path) -> str:
    m = re.search(pattern, path.read_text()) if path.is_file() else None
    return m.group(1) if m else "missing"


def versions(root: Path) -> dict[str, str]:
    found = {
        "pyproject.toml": _field(r'(?m)^version = "([^"]+)"', root / "pyproject.toml"),
        "cli/open_skill/__init__.py": _field(r'__version__ = "([^"]+)"', root / "cli/open_skill/__init__.py"),
        ".claude-plugin/plugin.json": _field(r'"version"\s*:\s*"([^"]+)"', root / ".claude-plugin/plugin.json"),
        "registry/adapters/open-skill.yaml": _field(r"""(?m)^tested_version:\s*["']?([^"'\s]+)""",
                                                    root / "registry/adapters/open-skill.yaml"),
    }
    # The files scripts/bump_version.py rewrites; every distinct pin in each one counts.
    for p in sorted([*root.glob("skills/*/SKILL.md"), root / "README.md", root / "README.vi.md"]):
        if p.is_file():
            for pin in sorted(set(re.findall(re.escape(GIT_URL) + r"@v([\w.\-]+)", p.read_text()))):
                found[f"{p.relative_to(root)} pin v{pin}"] = pin
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
