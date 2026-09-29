"""Compare the models named in Anthropic's prompting guide with registry/models profiles.

Exit 1 when the guide names a model that no profile matches exactly, so a maintainer can add one.
"""

import fnmatch
import re
import sys
import urllib.request
from pathlib import Path

import yaml

URL = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices"
# Only models with a dedicated guide count; older models are mentioned in passing in migration notes.
GUIDE = re.compile(r"prompting-claude-([a-z]+-\d+(?:-\d+)?)\b")


def model_ids(text: str) -> set[str]:
    return {f"claude-{slug}" for slug in GUIDE.findall(text)}


def uncovered(ids: set[str], profiles: list[dict]) -> list[str]:
    globs = [g for p in profiles if p["id"] != "generic" for g in p.get("match", [])]
    return sorted(i for i in ids if not any(fnmatch.fnmatch(i, g) for g in globs))


def main() -> int:
    req = urllib.request.Request(URL, headers={"User-Agent": "open-skill-standard model-watch"})
    text = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    profiles = [yaml.safe_load(p.read_text()) for p in sorted(Path("registry/models").glob("*.yaml"))]
    ids = model_ids(text)
    missing = uncovered(ids, profiles)
    print(f"models named in the guide: {', '.join(sorted(ids)) or 'none found'}")
    for m in missing:
        print(f"no profile matches: {m}")
    if not ids:
        print("could not find any model names; the page layout may have changed")
        return 1
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
