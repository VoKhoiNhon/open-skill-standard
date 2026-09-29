"""Where registry data and the user layer live."""

import os
from pathlib import Path

_PKG = Path(__file__).resolve().parent


def data_root() -> Path:
    """Repo checkout when running from source, packaged copy when installed."""
    repo = _PKG.parent.parent
    if (repo / "spec" / "taxonomy.yaml").is_file():
        return repo
    return _PKG / "_data"


def user_home() -> Path:
    return Path(os.environ.get("OPEN_SKILL_HOME", Path.home() / ".open-skill"))
