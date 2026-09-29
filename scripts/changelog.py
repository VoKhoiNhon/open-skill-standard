"""Print the CHANGELOG section for one version (used as GitHub release notes), or its release title.

Usage: python scripts/changelog.py [title] vX.Y.Z [CHANGELOG.md]
"""

import re
import sys
from pathlib import Path


def section(text: str, version: str) -> str:
    m = re.search(rf"(?ms)^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text)
    if not m:
        raise KeyError(f"no CHANGELOG section for {version}")
    return m.group(1).strip() + "\n"


def title(text: str, version: str) -> str:
    """`vX.Y.Z — <theme>`, the theme being the section's first line up to a colon or final period."""
    first = section(text, version).splitlines()[0]
    theme = re.split(r":|\.$", first, maxsplit=1)[0].strip()
    if not theme or theme.startswith("#"):
        return f"v{version}"
    # ponytail: lowercases a leading capital unless it starts an acronym ("CI"); a leading proper noun gets lowercased too.
    if theme[1:2].islower():
        theme = theme[0].lower() + theme[1:]
    return f"v{version} — {theme}"


if __name__ == "__main__":
    args = sys.argv[1:]
    render = section
    if args and args[0] == "title":
        render, args = title, args[1:]
    ver = args[0].removeprefix("v")
    sys.stdout.write(render(Path(args[1] if len(args) > 1 else "CHANGELOG.md").read_text(), ver) + ("\n" if render is title else ""))
