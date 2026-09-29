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


class NewerDataError(RuntimeError):
    """The user layer was written by a newer open-skill; writing with this one could lose data."""


def ensure_writable(home: Path) -> None:
    """Refuse writes from an older CLI; stamp the version on a fresh layer."""
    home = Path(home)
    v = data_version(home)
    if v > SCHEMA_VERSION:
        raise NewerDataError(
            f"{home} uses data schema {v}, newer than this open-skill understands ({SCHEMA_VERSION}). "
            "Upgrade open-skill before writing; reading still works."
        )
    if not (home / VERSION_FILE).exists() and v == SCHEMA_VERSION:
        write_version(home)


BACKUP_DIR = "backups"


def backup(home: Path, label: str = "manual") -> Path | None:
    """Zip the whole user layer (except older backups) to backups/<UTC time>-<label>.zip. None if nothing to save."""
    import time
    import zipfile

    home = Path(home)
    files = [p for p in sorted(home.rglob("*")) if p.is_file() and BACKUP_DIR not in p.relative_to(home).parts]
    if not files:
        return None
    dest = home / BACKUP_DIR / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{label}.zip"
    n = 1
    while dest.exists():
        n += 1
        dest = dest.with_name(f"{dest.stem.rsplit('.', 1)[0]}.{n}.zip")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(home).as_posix())
    return dest
