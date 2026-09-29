"""CI guard: user-layer files never tracked; no secrets, personal data or local paths in public content.

SVG images are checked by their text (labels, captures, alt text), not their geometry.
"""

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "cli"))
from open_skill.knowledge import looks_sensitive  # noqa: E402

FORBIDDEN_PATHS = (".open-skill/", "events.jsonl", "profile.yaml")
SCANNED = ("registry/", "skills/", "spec/", "evals/", "specs/", ".github/assets/", "README.md", "README.vi.md")
ALLOW = {"email": ("noreply", "users.noreply.github.com")}
LOCAL_PATH = re.compile(r"(?<![\w~])(/Users/|/home/)[A-Za-z0-9._-]+|\b[A-Za-z]:\\Users\\")  # a machine's home folder


def _reason(line: str) -> str | None:
    reason = looks_sensitive(line)
    if reason and not any(a in line for a in ALLOW.get(reason, ())):
        return reason
    return "local-path" if LOCAL_PATH.search(line) else None


def _svg_text(path: str) -> list[str]:
    root = ET.parse(path).getroot()
    return [t for el in root.iter() for t in (el.text, el.get("aria-label")) if t and t.strip()]


def check(files: list[str]) -> list[str]:
    problems = [f"tracked user-layer file: {f}" for f in files if any(p in f for p in FORBIDDEN_PATHS)]
    for f in files:
        if not f.startswith(SCANNED):
            continue
        if f.endswith(".svg"):
            problems += [f"{f}: text looks like {r}" for r in map(_reason, _svg_text(f)) if r]
        elif f.endswith((".md", ".yaml", ".yml", ".json")):
            for n, line in enumerate(Path(f).read_text(errors="replace").splitlines(), 1):
                reason = _reason(line)
                if reason:
                    problems.append(f"{f}:{n}: looks like {reason}")
    return problems


if __name__ == "__main__":
    files = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split()
    problems = check(files)
    print("\n".join(problems) or "privacy guard: clean")
    sys.exit(1 if problems else 0)
