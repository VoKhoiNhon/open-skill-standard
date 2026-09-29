import pytest

from open_skill import knowledge, upgrade, userdata

SEEDS = {"qa-engineer": [{"id": "flaky", "text": "A flaky test is a bug."}]}


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))
    return tmp_path / "h"


def test_upgrade_from_v0_layout(home):
    (home / "knowledge").mkdir(parents=True)
    (home / "profile.yaml").write_text("roles: {qa-engineer: 1.0}\n")
    (home / "knowledge" / "k-mine.md").write_text("---\nid: k-mine\ntype: lesson\nsource: user\napplies_to: ['role:*']\n---\nMine.\n")
    actions = upgrade.upgrade(SEEDS)
    assert actions[0].startswith("backed up to") and "added qa-engineer/flaky" in actions
    assert userdata.data_version(home) == userdata.SCHEMA_VERSION
    assert (home / "knowledge" / "k-mine.md").read_text().endswith("Mine.\n")
    assert upgrade.upgrade(SEEDS)[1:] == []


def test_upgrade_dry_run_touches_nothing(home):
    (home / "knowledge").mkdir(parents=True)
    (home / "profile.yaml").write_text("roles: {qa-engineer: 1.0}\n")
    before = sorted(p.name for p in home.rglob("*"))
    actions = upgrade.upgrade(SEEDS, dry_run=True)
    assert "would add qa-engineer/flaky" in actions
    assert sorted(p.name for p in home.rglob("*")) == before


def test_rollback_restores_state_before_upgrade(home):
    (home / "knowledge").mkdir(parents=True)
    (home / "profile.yaml").write_text("roles: {qa-engineer: 1.0}\n")
    upgrade.upgrade(SEEDS)
    assert any("flaky" in n["text"] for n in knowledge.load_knowledge())
    msg = upgrade.rollback()
    assert msg.startswith("restored") and not any("flaky" in n["text"] for n in knowledge.load_knowledge())


def test_rollback_without_backup(home):
    with pytest.raises(FileNotFoundError):
        upgrade.rollback()
