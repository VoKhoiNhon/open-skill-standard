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


def counts() -> dict[str, int]:
    """The registry numbers the pages show, so the site cannot drift from the registry it describes."""
    sys.path.insert(0, str(ROOT / "cli"))
    from open_skill import registry
    reg = registry.load(ROOT)
    return {"roles": len(reg.roles), "skills": sum(len(a.get("skills", [])) for a in reg.adapters.values()),
            "adapters": len(reg.adapters), "phases": len(reg.taxonomy["phases"]), "agents": len(reg.agents)}


def build(out: Path) -> Path:
    out = Path(out).resolve()  # the graph step runs in another directory
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "site", out)
    fill = counts()
    for page in out.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        for key, value in fill.items():
            text = text.replace(f"%%{key}%%", str(value))
        if "%%" in text:
            raise SystemExit(f"{page}: unknown placeholder {text[text.index('%%'):][:24]}")
        page.write_text(text, encoding="utf-8")
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
    if not (out / "graph.html").is_file():
        raise SystemExit(f"graph.html was not written to {out}")
    (out / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are, no Jekyll pass
    return out


if __name__ == "__main__":
    print(f"built {build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / '_site')}")
