import os
import subprocess
import sys

from open_skill import __version__


def test_version():
    out = subprocess.run([sys.executable, "-m", "open_skill", "--version"], capture_output=True, text=True)
    assert out.returncode == 0
    assert out.stdout.strip() == f"open-skill {__version__}"


def test_non_ascii_output_survives_a_legacy_code_page(tmp_path):
    """A pipe on Windows defaults to cp1252; Vietnamese task text must not crash the CLI."""
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "OPEN_SKILL_HOME": str(tmp_path / "home")}
    env.pop("PYTHONUTF8", None)
    p = subprocess.run([sys.executable, "-m", "open_skill", "route", "xuất hóa đơn ra CSV đang bị lỗi", "--explain",
                        "--no-record", "--project", str(tmp_path)], capture_output=True, env=env)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    out = p.stdout.decode("utf-8")
    assert "lỗi" in out and "→" in out
