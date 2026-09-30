"""Build the GitHub Pages site: site/ pages, the README images, and a live skill graph page.

Usage: python scripts/build_site.py [out_dir]   (default: _site)
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(out: Path) -> Path:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "site", out)
    shutil.copytree(ROOT / ".github" / "assets", out / "assets")
    # A clean HOME: the graph shows the registry, never the skills or notes of whoever builds it.
    with tempfile.TemporaryDirectory() as home:
        # An empty PATH too: tools detected on PATH (codegraph, graphify, ...) would show as installed.
        env = {**os.environ, "HOME": home, "USERPROFILE": home, "OPEN_SKILL_HOME": str(Path(home) / ".open-skill"),
               "PATH": home}
        for var in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "XDG_CONFIG_HOME", "CLAUDECODE"):
            env.pop(var, None)
        subprocess.run([sys.executable, "-m", "open_skill", "graph", "--format", "html", "--out", str(out / "graph.html")],
                       cwd=home, env=env, check=True, stdout=subprocess.DEVNULL)
    (out / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are, no Jekyll pass
    return out


if __name__ == "__main__":
    print(f"built {build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / '_site')}")
