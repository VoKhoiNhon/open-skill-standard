"""One safe step after pulling a new release: migrate user data, then sync starter knowledge."""

from . import knowledge, userdata

LABEL = "pre-upgrade"


def upgrade(seeds: dict[str, list], dry_run: bool = False) -> list[str]:
    home = knowledge.home()
    roles = list(knowledge.load_profile().get("roles", {}))
    actions: list[str] = []
    if not dry_run:
        saved = userdata.backup(home, LABEL)
        if saved:
            actions.append(f"backed up to {saved}")
    actions += userdata.migrate(home, dry_run=dry_run)
    if roles:
        actions += knowledge.sync_seeds(roles, seeds, dry_run=dry_run)
    return actions


def rollback() -> str:
    """Restore the newest pre-upgrade backup; the state being replaced is itself backed up first."""
    home = knowledge.home()
    candidates = [b for b in userdata.list_backups(home) if b.stem.endswith(f"-{LABEL}")]
    if not candidates:
        raise FileNotFoundError("no pre-upgrade backup to roll back to")
    safety = userdata.restore(home, candidates[-1])
    return f"restored {candidates[-1].name}" + (f"; the replaced state is in {safety.name}" if safety else "")
