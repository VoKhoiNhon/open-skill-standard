"""Where registry data and the user layer live."""

import contextlib
import errno
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


def folder(path) -> Path:
    """A folder the user named; FileNotFoundError (bad input) when it is not one, instead of globbing nothing."""
    path = Path(path)
    if not path.is_dir():
        raise FileNotFoundError(errno.ENOENT, "no such folder", str(path))
    return path


@contextlib.contextmanager
def locked(path: Path):
    """Exclusive lock on the file at path for the length of a read-modify-write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        try:
            import fcntl
        except ImportError:  # ponytail: no lock on Windows (no fcntl); use msvcrt.locking if concurrent writers appear there
            yield
            return
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
