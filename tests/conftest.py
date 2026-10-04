import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Env vars that move agent folders (registry/agents relocate entries). Tests use fixture homes only.
RELOCATION_VARS = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "XDG_CONFIG_HOME")


@pytest.fixture(autouse=True)
def _no_agent_relocation(monkeypatch):
    for var in RELOCATION_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True, scope="session")
def _home_is_the_fixture_home():
    """Tests point HOME at a fixture home. On Windows `~` expands to USERPROFILE, so `~` would reach the real home
    folder and its installed skills; expand it to HOME there too, as POSIX does. Session-wide, because module
    fixtures scan before function fixtures run."""
    if os.name != "nt":
        yield
        return
    import ntpath
    real = ntpath.expanduser

    def expanduser(path):
        p, home = os.fspath(path), os.environ.get("HOME")
        if home and isinstance(p, str) and (p == "~" or p.startswith(("~/", "~\\"))):
            return home + p[1:]
        return real(path)

    mp = pytest.MonkeyPatch()
    mp.setattr(ntpath, "expanduser", expanduser)
    yield
    mp.undo()


GRAPHIFY_FIXTURE = Path(__file__).parent / "fixtures" / "graphify" / "graph.json"
# Source files the fixture graph names; the import lines match its source_location values.
GRAPH_SOURCES = {
    "pkg/__init__.py": "",
    "pkg/route.py": "def fit():\n    return 1\n\ndef target_phase():\n    return 2\n",
    "pkg/cli.py": "from pkg import route\n\ndef cmd_route():\n    return route.target_phase()\n",
    "pkg/deep.py": "from pkg import cli\n\ndef run():\n    return cli.cmd_route()\n",
    "pkg/far.py": "from pkg import deep\n\ndef x():\n    return deep.run()\n",
    "tests/test_route.py": "import pathlib\n\nfrom pkg import (\n    route,\n)\n\ndef test_fit():\n    assert route.fit() == 1\n",
    "tests/test_cli.py": "from pkg import cli as c\n\ndef test_cmd():\n    assert c.cmd_route() == 2\n",
}


def git(root, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=root,
                          capture_output=True, text=True, check=True).stdout


@pytest.fixture
def graph_project(tmp_path):
    """A committed git project with Graphify output shaped like the real tool's (package imports hit __init__.py)."""
    root = tmp_path / "proj"
    for rel, text in GRAPH_SOURCES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    (root / "graphify-out").mkdir()
    shutil.copy(GRAPHIFY_FIXTURE, root / "graphify-out" / "graph.json")
    (root / ".gitignore").write_text("graphify-out/\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "init")
    return root


@pytest.fixture
def fake_graphify(tmp_path, monkeypatch):
    """Put a stand-in `graphify` first on PATH; returns a setter for its exit code/stderr and the call log path."""
    bin_dir, log = tmp_path / "bin", tmp_path / "graphify-calls.log"
    bin_dir.mkdir()
    program = bin_dir / "fake_graphify.py"
    # A launcher Windows finds through PATHEXT, and a shell script elsewhere; both run the Python stand-in.
    if os.name == "nt":
        (bin_dir / "graphify.cmd").write_text(f'@"{sys.executable}" "{program}" %*\n', encoding="utf-8")
    else:
        launcher = bin_dir / "graphify"
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{program}" "$@"\n', encoding="utf-8")
        launcher.chmod(0o755)

    def configure(exit_code=0, stderr=""):
        program.write_text(
            "import os, sys\n"
            f"with open({str(log)!r}, 'a', encoding='utf-8') as f:\n"
            "    f.write(' '.join([os.path.realpath(os.getcwd()), *sys.argv[1:]]) + '\\n')\n"
            f"sys.stderr.write({stderr!r})\n"
            f"sys.exit({exit_code})\n", encoding="utf-8")
        return log

    configure()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return configure


def _can_symlink() -> bool:
    """Whether this user may create symbolic links; Windows allows it only with Developer Mode or as administrator."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        try:
            os.symlink(d, os.path.join(d, "link"), target_is_directory=True)
        except (OSError, NotImplementedError):
            return False
    return True


def pytest_configure(config):
    config.addinivalue_line("markers", "symlinks: the test creates symbolic links")


def pytest_collection_modifyitems(config, items):
    marked = [item for item in items if "symlinks" in item.keywords]
    if marked and not _can_symlink():
        skip = pytest.mark.skip(reason="this user cannot create symbolic links (on Windows, turn on Developer Mode)")
        for item in marked:
            item.add_marker(skip)
