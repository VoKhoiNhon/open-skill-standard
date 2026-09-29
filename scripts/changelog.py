"""Print the CHANGELOG section for one version (used as GitHub release notes)."""

import re
import sys
from pathlib import Path


def section(text: str, version: str) -> str:
    m = re.search(rf"(?ms)^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text)
    if not m:
        raise KeyError(f"no CHANGELOG section for {version}")
    return m.group(1).strip() + "\n"


if __name__ == "__main__":
    ver = sys.argv[1].removeprefix("v")
    sys.stdout.write(section(Path(sys.argv[2] if len(sys.argv) > 2 else "CHANGELOG.md").read_text(), ver))
