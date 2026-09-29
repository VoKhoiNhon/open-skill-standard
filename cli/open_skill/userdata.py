"""Safety primitives for the user layer (~/.open-skill): atomic writes, schema version, backups, migrations."""

import os
import tempfile
from pathlib import Path


def atomic_write(path: Path, text: str) -> None:
    """Write via a temp file in the same folder and rename, so a crash never leaves a half-written file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


SCHEMA_VERSION = 1
VERSION_FILE = "VERSION"
_MARKERS = ("profile.yaml", "knowledge", "events.jsonl")


def data_version(home: Path) -> int:
    """Schema version of an existing user layer; 0 for layouts written before versioning existed."""
    home = Path(home)
    vf = home / VERSION_FILE
    if vf.is_file():
        return int(vf.read_text().strip() or 0)
    return 0 if any((home / m).exists() for m in _MARKERS) else SCHEMA_VERSION


def write_version(home: Path, version: int = SCHEMA_VERSION) -> None:
    atomic_write(Path(home) / VERSION_FILE, f"{version}\n")
