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
    with path.open("a", encoding="utf-8") as f:
        try:
            import fcntl
        except ImportError:  # Windows
            with _msvcrt_locked(f):
                yield
            return
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


@contextlib.contextmanager
def _msvcrt_locked(f):
    """Lock the first byte of f; msvcrt has no blocking wait of its own (LK_LOCK gives up after 10 s), so poll."""
    import msvcrt
    import time

    f.seek(0)
    while True:
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            break
        except OSError as e:
            if e.errno not in (errno.EACCES, errno.EDEADLOCK):  # held by another process; anything else is real
                raise
            time.sleep(0.01)
    try:
        yield
    finally:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
