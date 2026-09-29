import subprocess
import sys

from open_skill import __version__


def test_version():
    out = subprocess.run([sys.executable, "-m", "open_skill", "--version"], capture_output=True, text=True)
    assert out.returncode == 0
    assert out.stdout.strip() == f"open-skill {__version__}"
