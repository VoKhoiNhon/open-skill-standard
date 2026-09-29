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


def _files(home: Path) -> list[Path]:
    """Every file in the user layer, following linked folders (a notes folder on a synced drive) once each."""
    out, seen = [], set()
    for d, dirs, names in os.walk(home, followlinks=True):
        real = os.path.realpath(d)
        if real in seen:
            dirs[:] = []
            continue
        seen.add(real)
        out += [Path(d) / n for n in names if (Path(d) / n).is_file()]
    return sorted(out)


def backup(home: Path, label: str = "manual") -> Path | None:
    """Zip the whole user layer (except older backups) to backups/<UTC time>-<label>.zip. None if nothing to save."""
    import datetime as dt
    import zipfile

    home = Path(home)
    files = [p for p in _files(home) if BACKUP_DIR not in p.relative_to(home).parts]
    if not files:
        return None
    (home / BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    while True:  # microsecond UTC stamps sort in creation order; loop only on a same-microsecond clash
        dest = home / BACKUP_DIR / f"{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%S%fZ}-{label}.zip"
        if not dest.exists():
            break
    part = dest.with_name(f".{dest.name}.part")  # renamed once complete: backups/*.zip are always whole archives
    try:
        with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, p.relative_to(home).as_posix())
        os.replace(part, dest)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return dest


def list_backups(home: Path) -> list[Path]:
    return sorted((Path(home) / BACKUP_DIR).glob("*.zip"))


def prune_backups(home: Path, label: str, keep: int = 10) -> list[Path]:
    """Delete all but the newest `keep` backups with this label; other labels (manual ones) are never touched."""
    mine = [p for p in list_backups(home) if p.stem.split(".")[0].endswith(f"-{label}")]
    doomed = mine[:-keep] if keep else mine
    for p in doomed:
        p.unlink()
    return doomed


class UnsafeBackupError(ValueError):
    """A backup archive contains paths that would escape the user layer."""


def _check_members(names: list[str]) -> None:
    for n in names:
        parts = Path(n).parts
        if Path(n).is_absolute() or ".." in parts or (parts and parts[0] == BACKUP_DIR):
            raise UnsafeBackupError(f"refusing to restore unsafe path: {n}")


def restore(home: Path, archive: Path) -> Path | None:
    """Replace the user layer with an archive's content. The current state is backed up first; backups/ is kept."""
    import shutil
    import zipfile

    home = Path(home)
    with zipfile.ZipFile(archive) as z:
        _check_members(z.namelist())
        safety = backup(home, "before-restore")
        staging = Path(tempfile.mkdtemp(dir=home if home.exists() else None, prefix=".restore-"))
        z.extractall(staging)
    home.mkdir(parents=True, exist_ok=True)
    for entry in home.iterdir():
        if entry.name not in (BACKUP_DIR, staging.name):
            shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    for entry in staging.iterdir():
        os.replace(entry, home / entry.name)
    staging.rmdir()
    return safety


# version -> (summary, step). A step upgrades data from `version` to `version + 1` and returns what it
# changed (or would change, when dry_run is true). Steps must be idempotent and must not alter user text.
MIGRATIONS: dict = {}


def pending(home: Path) -> list[int]:
    return list(range(data_version(home), SCHEMA_VERSION))


def migrate(home: Path, dry_run: bool = False) -> list[str]:
    """Bring the user layer to SCHEMA_VERSION, backing it up first. Returns a description of each change."""
    home = Path(home)
    v = data_version(home)
    if v > SCHEMA_VERSION:
        raise NewerDataError(f"{home} uses data schema {v}; this open-skill understands up to {SCHEMA_VERSION}.")
    steps = pending(home)
    if not steps:
        return []
    actions: list[str] = []
    if not dry_run:
        saved = backup(home, f"pre-migrate-v{v}")
        if saved:
            actions.append(f"backed up to {saved}")
    for step in steps:
        summary, fn = MIGRATIONS[step]
        actions.append(f"v{step} -> v{step + 1}: {summary}")
        actions += [f"  {a}" for a in fn(home, dry_run)]
        if not dry_run:
            write_version(home, step + 1)
    return actions


def text_hash(text: str) -> str:
    """Hash of a note's text ignoring case, runs of whitespace and Unicode normalization (an editor that saves NFD
    does not make an untouched note look edited). Unchanged for NFC text, so stored hashes stay valid."""
    import hashlib
    import re
    import unicodedata

    return hashlib.sha1(re.sub(r"\s+", " ", unicodedata.normalize("NFC", text).strip().lower()).encode()).hexdigest()[:12]


def _split_note(raw: str) -> tuple[str, str]:
    """(frontmatter yaml, body) split textually so the body is preserved byte for byte."""
    if raw.startswith("---\n"):
        end = raw.find("\n---\n", 4)
        if end != -1:
            return raw[4:end], raw[end + 5 :]
    return "", raw


def note_meta(fm: str) -> dict | None:
    """Frontmatter of a note as a dict; None when it is missing, not a mapping or not valid YAML."""
    import yaml

    try:
        meta = yaml.safe_load(fm) if fm else None
    except yaml.YAMLError:
        return None
    return meta if isinstance(meta, dict) else None


def _m0_to_1(home: Path, dry_run: bool) -> list[str]:
    """Stamp notes with `schema: 1`; seed notes also record the hash of their text as `seed_hash`."""
    import yaml

    changed = []
    for p in sorted((Path(home) / "knowledge").glob("*.md")):
        fm, body = _split_note(p.read_text(encoding="utf-8"))
        meta = note_meta(fm)
        if meta is None and fm:
            changed.append(f"left as is {p.name}: its frontmatter is not valid YAML")
            continue
        if meta is None or meta.get("schema") == 1:
            continue
        meta["schema"] = 1
        if meta.get("source") == "seed" and "seed_hash" not in meta:
            meta["seed_hash"] = text_hash(body)
        changed.append(f"{'would update' if dry_run else 'updated'} {p.name}")
        if not dry_run:
            atomic_write(p, "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n" + body)
    return changed


MIGRATIONS[0] = ("stamp notes with a schema version and record seed provenance", _m0_to_1)
