import subprocess
import sys


def test_version():
    out = subprocess.run([sys.executable, "-m", "open_skill", "--version"], capture_output=True, text=True)
    assert out.returncode == 0
    assert out.stdout.strip().startswith("open-skill 0.1")
