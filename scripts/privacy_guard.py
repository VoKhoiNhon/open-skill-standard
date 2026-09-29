"""CI guard: user-layer files never tracked; no secrets, personal data or local paths in any public text file.

SVG images are checked by their text (labels, captures, alt text), not their geometry.
"""

import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cli"))
from open_skill.knowledge import SENSITIVE  # noqa: E402

FORBIDDEN_PATHS = (".open-skill/", "events.jsonl", "profile.yaml")
# Every tracked text file is public; tests are skipped because they hold fake secrets on purpose.
SKIPPED = ("tests/", "uv.lock")
TEXT = (".md", ".yaml", ".yml", ".json", ".py", ".sh", ".toml", ".txt", ".mmd", ".cfg", ".ini", "")
ALLOW = {"email": ("noreply", "users.noreply.github.com")}
LOCAL_PATH = re.compile(r"(?<![\w~])(/Users/|/home/)[A-Za-z0-9._-]+|\b[A-Za-z]:\\Users\\")  # a machine's home folder


def _reason(line: str) -> str | None:
    """The first kind of sensitive text on the line; an allowed match (a noreply address) excuses only itself."""
    for name, rx in SENSITIVE:
        if any(not any(a in m.group() for a in ALLOW.get(name, ())) for m in rx.finditer(line)):
            return name
    return "local-path" if LOCAL_PATH.search(line) else None


def _svg_text(path: str) -> list[str]:
    root = ET.parse(path).getroot()
    return [t for el in root.iter() for t in (el.text, el.get("aria-label")) if t and t.strip()]


def check(files: list[str]) -> list[str]:
    problems = [f"tracked user-layer file: {f}" for f in files if any(p in f for p in FORBIDDEN_PATHS)]
    for f in files:
        if f.startswith(SKIPPED):
            continue
        if f.endswith(".svg"):
            problems += [f"{f}: text looks like {r}" for r in map(_reason, _svg_text(f)) if r]
        elif Path(f).suffix in TEXT:
            for n, line in enumerate(Path(f).read_text(errors="replace").splitlines(), 1):
                reason = _reason(line)
                if reason:
                    problems.append(f"{f}:{n}: looks like {reason}")
    return problems


def git_env() -> dict:
    """The environment without GIT_DIR and friends, so git works on the folder it is run in (cwd)."""
    return {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}


def tracked(root: Path) -> list[str]:
    """Tracked paths relative to root; -z keeps spaces and non-ASCII names exactly as they are."""
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True, check=True,
                         env=git_env()).stdout
    return [f for f in out.split("\0") if f]


def main(root: Path = ROOT) -> int:
    os.chdir(root)  # check() reads paths relative to the repository root, wherever the script is run from
    problems = check(tracked(root))
    print("\n".join(problems) or "privacy guard: clean")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
