"""Set one version everywhere it appears, and pin skills to the matching release tag.

Usage: python scripts/bump_version.py 0.3.0 [--root .]
"""

import argparse
import re
import sys
from pathlib import Path

GIT_URL = "git+https://github.com/VoKhoiNhon/open-skill-standard"

RULES = [
    ("pyproject.toml", r'(?m)^version = "[^"]+"', 'version = "{v}"'),
    ("cli/open_skill/__init__.py", r'__version__ = "[^"]+"', '__version__ = "{v}"'),
    (".claude-plugin/plugin.json", r'"version": "[^"]+"', '"version": "{v}"'),
    ("registry/adapters/open-skill.yaml", r"(?m)^tested_version: .+$", "tested_version: {v}"),
]


def pin(text: str, v: str) -> str:
    """Point every `uvx --from git+...open-skill-standard[@ref]` at the release tag."""
    return re.sub(re.escape(GIT_URL) + r"(@[\w.\-]+)?(?=[\s`\"')])", f"{GIT_URL}@v{v}", text)


def bump(root: Path, v: str) -> list[str]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        raise ValueError(f"not a semantic version: {v}")
    changed = []
    for rel, pattern, repl in RULES:
        p = root / rel
        text = p.read_text(encoding="utf-8")
        new, n = re.subn(pattern, repl.format(v=v), text, count=1)
        if n != 1:
            raise ValueError(f"version pattern not found in {rel}")
        if new != text:
            p.write_text(new, encoding="utf-8", newline="\n")
            changed.append(rel)
    for p in sorted([*root.glob("skills/*/SKILL.md"), root / "README.md", root / "README.vi.md", *root.glob("site/**/*.html")]):
        if p.exists():
            text = p.read_text(encoding="utf-8")
            new = pin(text, v)
            if new != text:
                p.write_text(new, encoding="utf-8", newline="\n")
                changed.append(p.relative_to(root).as_posix())
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    for f in bump(Path(a.root), a.version):
        print(f"updated {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
