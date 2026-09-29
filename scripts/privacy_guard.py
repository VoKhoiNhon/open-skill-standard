"""CI guard: user-layer files never tracked; no secrets or personal data in public registry content."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "cli"))
from open_skill.knowledge import looks_sensitive  # noqa: E402

FORBIDDEN_PATHS = (".open-skill/", "events.jsonl", "profile.yaml")
SCANNED = ("registry/", "skills/", "spec/", "evals/", "specs/", "README.md", "README.vi.md")
ALLOW = {"email": ("noreply", "users.noreply.github.com")}

files = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split()
problems = [f"tracked user-layer file: {f}" for f in files if any(p in f for p in FORBIDDEN_PATHS)]
for f in files:
    if not f.startswith(SCANNED) or not f.endswith((".md", ".yaml", ".yml", ".json")):
        continue
    for n, line in enumerate(Path(f).read_text(errors="replace").splitlines(), 1):
        reason = looks_sensitive(line)
        if reason and not any(a in line for a in ALLOW.get(reason, ())):
            problems.append(f"{f}:{n}: looks like {reason}")
print("\n".join(problems) or "privacy guard: clean")
sys.exit(1 if problems else 0)
