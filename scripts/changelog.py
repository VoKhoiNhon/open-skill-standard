"""Print the CHANGELOG section for one version (used as GitHub release notes), or its release title.

Usage: python scripts/changelog.py [title] vX.Y.Z [CHANGELOG.md]
"""

import re
import sys
from pathlib import Path


def section(text: str, version: str) -> str:
    # A section ends at the next version heading or at the link references closing the file.
    m = re.search(rf"(?ms)^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]\n]+\]: |\Z)", text)
    if not m:
        raise KeyError(f"no CHANGELOG section for {version}")
    return m.group(1).strip() + "\n"


def title(text: str, version: str) -> str:
    """`vX.Y.Z — <theme>`, the theme being the section's first line up to a colon or final period."""
    first = section(text, version).splitlines()[0]
    theme = re.split(r":|\.$", first, maxsplit=1)[0].strip()
    if not theme or theme.startswith("#"):
        return f"v{version}"
    # Lowercase an ordinary capitalized first word, not an acronym (CI) or a brand with inner capitals (GitHub).
    # ponytail: a plain proper noun ("Python") still gets lowercased; keep a list of names if that starts to matter.
    first = theme.split()[0]
    if first[1:].islower():
        theme = theme[0].lower() + theme[1:]
    return f"v{version} — {theme}"


if __name__ == "__main__":
    args = sys.argv[1:]
    render = section
    if args and args[0] == "title":
        render, args = title, args[1:]
    ver, path = args[0].removeprefix("v"), Path(args[1] if len(args) > 1 else "CHANGELOG.md")
    try:
        out = render(path.read_text(encoding="utf-8"), ver)
    except KeyError:
        sys.exit(f"::error::{path.name} has no section for {ver}; add ## [{ver}] - YYYY-MM-DD before tagging (see RELEASING.md)")
    sys.stdout.write(out + ("\n" if render is title else ""))
