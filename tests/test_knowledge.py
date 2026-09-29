import json
import time
import zipfile

import pytest
import yaml

from open_skill import frontmatter, knowledge


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_SKILL_HOME", str(tmp_path / "h"))
    return tmp_path / "h"


def test_init_writes_profile_and_seeds(home):
    knowledge.init({"roles": {"data-engineer": 1.0}, "stack": ["python"]},
                   seeds={"data-engineer": [{"id": "merge", "text": "Use MERGE on the business key."}]})
    prof = yaml.safe_load((home / "profile.yaml").read_text())
    assert prof["roles"] == {"data-engineer": 1.0}
    nodes = knowledge.load_knowledge()
    assert len(nodes) == 1
    assert nodes[0]["source"] == "seed" and nodes[0]["applies_to"] == ["role:data-engineer"]
    assert nodes[0]["seed_id"] == "data-engineer/merge"


def test_learn_dedupes_and_merges_scope(home):
    a = knowledge.learn("Use MERGE, not INSERT", ["skill:x"])
    b = knowledge.learn("use merge, not insert ", ["project:/p"])
    assert a == b
    [node] = knowledge.load_knowledge()
    assert set(node["applies_to"]) == {"skill:x", "project:/p"}


def test_learn_rejects_sensitive_unless_forced(home):
    with pytest.raises(ValueError):
        knowledge.learn("token ghp_abcdefghijklmnopqrstuvwxyz0123456789", ["skill:x"])
    assert knowledge.learn("token ghp_abcdefghijklmnopqrstuvwxyz0123456789", ["skill:x"], force=True)


@pytest.mark.parametrize("text", ["mail me at a.b@example.com", "call +84 912 345 678", "key sk-ABCDEFGHIJKLMNOPQRSTUV",
                                  "AKIAABCDEFGHIJKLMNOP", "password=hunter2", "-----BEGIN PRIVATE KEY-----"])
def test_looks_sensitive(text):
    assert knowledge.looks_sensitive(text)


def test_looks_sensitive_allows_normal_text():
    assert knowledge.looks_sensitive("Backfill in batches of 7 days; check nulls on 2 keys") is None
    assert knowledge.looks_sensitive("verified: 2026-09-29, version 1.6.0") is None
    assert knowledge.looks_sensitive("pin it: uvx --from git+https://example.org/repo@v0.2.0 tool") is None
    assert knowledge.looks_sensitive("npm i left-pad@1.3.0") is None


def test_forget(home):
    nid = knowledge.learn("a lesson", ["skill:x"])
    assert knowledge.forget(nid) is True
    assert knowledge.forget(nid) is False


def test_personal_weights_from_feedback(home):
    knowledge.record({"type": "proposed", "route_id": "r1",
                      "chain": [{"id": "s/a", "invoke": "a"}, {"id": "s/b", "invoke": "b"}]})
    knowledge.record({"type": "feedback", "route_id": "r1", "ran": ["a", "c"], "outcome": "ok"})
    w = knowledge.personal_weights()
    assert w["s/a"] > 0 and w["s/b"] < 0 and w["invoke:c"] > 0


def test_weights_decay_with_half_life(home):
    now = time.time()
    old = now - 90 * 86400
    knowledge.record({"type": "proposed", "route_id": "r1", "chain": [{"id": "s/a", "invoke": "a"}], "ts": old})
    knowledge.record({"type": "feedback", "route_id": "r1", "ran": ["a"], "outcome": "ok", "ts": old})
    assert knowledge.personal_weights(now=now)["s/a"] == pytest.approx(0.5, rel=1e-3)


def test_export_excludes_events(home, tmp_path):
    knowledge.init({"roles": {"qa-engineer": 1.0}}, seeds={})
    knowledge.learn("a lesson", ["skill:x"])
    knowledge.record({"type": "proposed", "route_id": "r", "chain": []})
    names = zipfile.ZipFile(knowledge.export(tmp_path / "out")).namelist()
    assert "profile.yaml" in names and any(n.startswith("knowledge/") for n in names)
    assert not any("events" in n for n in names)


def test_import_agent_memory(home, tmp_path):
    mem = tmp_path / "projects" / "-Users-me-app" / "memory"
    mem.mkdir(parents=True)
    (mem / "MEMORY.md").write_text("- index")
    (mem / "prefers-uv.md").write_text("---\nname: prefers-uv\ndescription: Use uv\nmetadata:\n  type: feedback\n---\nAlways use uv for Python.")
    (mem / "secret.md").write_text("---\nname: s\n---\npassword=abc")
    assert knowledge.import_agent_memory(tmp_path / "projects") == 1
    [node] = knowledge.load_knowledge()
    assert node["source"] == "agent-memory" and node["type"] == "preference"
    assert "uv" in node["text"]
    assert (mem / "prefers-uv.md").read_text().startswith("---")  # untouched


def test_knowledge_file_has_valid_frontmatter(home):
    nid = knowledge.learn("Staged backfills", ["role:data-engineer"], type_="pitfall")
    meta, body = frontmatter.parse((home / "knowledge" / f"{nid}.md").read_text())
    assert meta["type"] == "pitfall" and body.strip() == "Staged backfills"
    assert json.loads(json.dumps(meta))


def test_load_profile_missing_is_empty(home):
    assert knowledge.load_profile() == {}


def test_writes_refused_when_data_is_newer(home):
    from open_skill import userdata
    userdata.write_version(home, userdata.SCHEMA_VERSION + 1)
    with pytest.raises(userdata.NewerDataError):
        knowledge.learn("anything", ["role:*"])
    with pytest.raises(userdata.NewerDataError):
        knowledge.record({"type": "proposed", "route_id": "r", "chain": []})


def test_first_write_stamps_version(home):
    knowledge.learn("a lesson", ["role:*"])
    assert (home / "VERSION").exists()


def test_old_layout_is_migrated_with_backup_before_first_write(home, capsys):
    from open_skill import userdata
    (home / "knowledge").mkdir(parents=True)
    (home / "knowledge" / "k-old.md").write_text("---\nid: k-old\ntype: pitfall\nsource: seed\napplies_to: [role:qa-engineer]\n---\nOld seed text\n")
    knowledge.learn("A new lesson", ["role:qa-engineer"])
    assert userdata.data_version(home) == userdata.SCHEMA_VERSION
    assert userdata.list_backups(home)
    assert "upgraded your data" in capsys.readouterr().err
    assert (home / "knowledge" / "k-old.md").read_text().endswith("Old seed text\n")


SEEDS_V1 = {"data-engineer": [{"id": "merge", "text": "Use MERGE on the key."},
                              {"id": "nulls", "text": "Check nulls on keys."}]}


def _note(sid):
    for n in knowledge.load_knowledge():
        if n.get("seed_id") == sid:
            return n


def test_sync_adds_then_is_idempotent(home):
    added = knowledge.sync_seeds(["data-engineer"], SEEDS_V1)
    assert added == ["added data-engineer/merge", "added data-engineer/nulls"]
    assert _note("data-engineer/merge")["text"] == "Use MERGE on the key."
    assert knowledge.sync_seeds(["data-engineer"], SEEDS_V1) == []


def test_sync_updates_untouched_but_keeps_user_edits(home):
    knowledge.sync_seeds(["data-engineer"], SEEDS_V1)
    edited = next(p for p in (home / "knowledge").glob("*.md") if "nulls" in p.read_text())
    edited.write_text(edited.read_text().replace("Check nulls on keys.", "Check nulls AND duplicates on keys (my rule)."))
    v2 = {"data-engineer": [{"id": "merge", "text": "Use MERGE on the business key."},
                            {"id": "nulls", "text": "Check nulls on primary keys."}]}
    actions = knowledge.sync_seeds(["data-engineer"], v2)
    assert "updated data-engineer/merge (you had not edited it)" in actions
    assert any(a.startswith("kept your edit of data-engineer/nulls") for a in actions)
    assert knowledge.proposals()["data-engineer/nulls"] == "Check nulls on primary keys."
    assert _note("data-engineer/merge")["text"] == "Use MERGE on the business key."
    assert "(my rule)" in _note("data-engineer/nulls")["text"]


def test_sync_respects_dismissed_and_reports_retired(home):
    knowledge.sync_seeds(["data-engineer"], SEEDS_V1)
    knowledge.forget(_note("data-engineer/nulls")["id"])
    assert "data-engineer/nulls" in knowledge.dismissed_seeds()
    v2 = {"data-engineer": [{"id": "nulls", "text": "Check nulls on keys."}]}
    actions = knowledge.sync_seeds(["data-engineer"], v2)
    assert _note("data-engineer/nulls") is None
    assert "kept data-engineer/merge: no longer shipped upstream" in actions


def test_sync_adopts_pre_id_seed_notes(home):
    knowledge.learn("Use MERGE on the key.", ["role:data-engineer"], type_="pitfall", source="seed")
    actions = knowledge.sync_seeds(["data-engineer"], SEEDS_V1)
    assert any(a.startswith("linked data-engineer/merge") for a in actions)
    assert len([n for n in knowledge.load_knowledge() if "MERGE" in n["text"]]) == 1


def test_sync_dry_run_writes_nothing(home):
    actions = knowledge.sync_seeds(["data-engineer"], SEEDS_V1, dry_run=True)
    assert actions == ["would add data-engineer/merge", "would add data-engineer/nulls"]
    assert not (home / "knowledge").exists() or not list((home / "knowledge").glob("*.md"))


def test_sync_is_quiet_about_edits_when_upstream_did_not_change(home):
    knowledge.sync_seeds(["data-engineer"], SEEDS_V1)
    p = next(p for p in (home / "knowledge").glob("*.md") if "nulls" in p.read_text())
    p.write_text(p.read_text().replace("Check nulls on keys.", "Check nulls on keys, always."))
    assert knowledge.sync_seeds(["data-engineer"], SEEDS_V1) == []



def test_retired_seeds_are_reported_once(home):
    knowledge.sync_seeds(["data-engineer"], SEEDS_V1)
    v2 = {"data-engineer": [SEEDS_V1["data-engineer"][1]]}
    assert knowledge.sync_seeds(["data-engineer"], v2) == ["kept data-engineer/merge: no longer shipped upstream"]
    assert knowledge.sync_seeds(["data-engineer"], v2) == []
    assert _note("data-engineer/merge")["retired"] is True
    knowledge.sync_seeds(["data-engineer"], SEEDS_V1)
    assert "retired" not in _note("data-engineer/merge")


def _edit_and_change_upstream(home):
    knowledge.sync_seeds(["data-engineer"], SEEDS_V1)
    p = next(p for p in (home / "knowledge").glob("*.md") if "nulls" in p.read_text())
    p.write_text(p.read_text().replace("Check nulls on keys.", "My stricter null rule."))
    v2 = {"data-engineer": [{"id": "nulls", "text": "Check nulls on primary keys."}]}
    knowledge.sync_seeds(["data-engineer"], v2)
    return v2


def test_accept_proposal_takes_upstream_after_backup(home):
    from open_skill import userdata
    v2 = _edit_and_change_upstream(home)
    saved = knowledge.accept_proposal("data-engineer/nulls")
    assert saved and saved in userdata.list_backups(home)
    assert _note("data-engineer/nulls")["text"] == "Check nulls on primary keys."
    assert knowledge.proposals() == {} and knowledge.sync_seeds(["data-engineer"], v2) == []


def test_keep_mine_silences_that_upstream_wording(home):
    v2 = _edit_and_change_upstream(home)
    knowledge.keep_mine("data-engineer/nulls")
    assert _note("data-engineer/nulls")["text"] == "My stricter null rule."
    assert knowledge.proposals() == {} and knowledge.sync_seeds(["data-engineer"], v2) == []
    v3 = {"data-engineer": [{"id": "nulls", "text": "Check nulls on all keys."}]}
    assert any("kept your edit" in a for a in knowledge.sync_seeds(["data-engineer"], v3))


def test_bug_a_skill_run_instead_of_the_proposed_one_is_credited_to_its_id(home):
    # The router skill says to record corrections ("use superpowers here, not spec-kit") with feedback;
    # the skill that ran was stored as "invoke:<name>", a key routing never reads.
    knowledge.record({"type": "proposed", "route_id": "r1", "chain": [{"id": "spec-kit/plan", "invoke": "speckit-plan"}]})
    knowledge.record({"type": "feedback", "route_id": "r1", "ran": ["superpowers:writing-plans"], "outcome": "ok"})
    w = knowledge.personal_weights(names={"superpowers:writing-plans": "superpowers/writing-plans"})
    assert w["superpowers/writing-plans"] > 0 and w["spec-kit/plan"] < 0


def test_bug_feedback_naming_a_proposed_step_by_its_id_counts_as_run(home):
    knowledge.record({"type": "proposed", "route_id": "r1", "chain": [{"id": "s/a", "invoke": "a"}]})
    knowledge.record({"type": "feedback", "route_id": "r1", "ran": ["s/a"], "outcome": "ok"})
    assert knowledge.personal_weights()["s/a"] > 0


def test_bug_reading_notes_on_a_fresh_home_made_the_first_write_look_like_an_upgrade(home, capsys):
    # load_knowledge() used to create an empty knowledge/ folder, so the next write saw an unversioned layout,
    # "migrated" it and printed "upgraded your data" on a machine that had never run open-skill.
    from open_skill import userdata
    assert knowledge.load_knowledge() == []
    knowledge.record({"type": "proposed", "route_id": "r-1", "task": "t", "chain": []})
    assert "upgraded your data" not in capsys.readouterr().err
    assert userdata.data_version(home) == userdata.SCHEMA_VERSION
    assert not userdata.list_backups(home)


def test_bug_seed_dry_run_created_folders_on_a_fresh_home(home):
    assert knowledge.sync_seeds(["data-engineer"], SEEDS_V1, dry_run=True) == [
        "would add data-engineer/merge", "would add data-engineer/nulls"]
    assert not home.exists()


def test_bug_dry_run_said_it_saved_upstream_wording_and_kept_retired_seeds(home):
    # A dry run reported "upstream wording saved for review" and "kept ...", past tense, while writing nothing.
    knowledge.sync_seeds(["data-engineer"], SEEDS_V1)
    edited = next(p for p in (home / "knowledge").glob("*.md") if "nulls" in p.read_text())
    edited.write_text(edited.read_text().replace("Check nulls on keys.", "Check nulls AND duplicates (my rule)."))
    v2 = {"data-engineer": [{"id": "nulls", "text": "Check nulls on primary keys."}]}
    assert knowledge.sync_seeds(["data-engineer"], v2, dry_run=True) == [
        "would keep your edit of data-engineer/nulls; upstream wording would wait for review "
        "(open-skill seeds diff data-engineer/nulls)",
        "would keep data-engineer/merge: no longer shipped upstream"]
    assert knowledge.proposals() == {}


# Seeds as a Vietnamese-speaking user may have them from an early install, and the English wording that replaces them.
SEEDS_VI = {"data-engineer": [{"id": "merge", "text": "Dùng MERGE theo khoá nghiệp vụ thay vì INSERT."},
                              {"id": "nulls", "text": "Kiểm tra null và trùng lặp trên khoá sau mỗi lần nạp."}]}
SEEDS_EN = {"data-engineer": [{"id": "merge", "text": "Use MERGE on the business key instead of a blind INSERT."},
                              {"id": "nulls", "text": "Check nulls and duplicates on primary and business keys after every load."}]}


def test_upgrade_from_vietnamese_seeds_keeps_the_users_edit_and_the_ids(home):
    from open_skill import upgrade
    knowledge.init({"roles": {"data-engineer": 1.0}}, seeds=SEEDS_VI)
    before = {n["seed_id"]: n["id"] for n in knowledge.load_knowledge()}
    edited = next(p for p in (home / "knowledge").glob("*.md") if "trùng lặp" in p.read_text())
    mine = edited.read_text().replace("sau mỗi lần nạp.", "sau mỗi lần nạp, kể cả bảng tạm (quy tắc của tôi).")
    edited.write_text(mine)

    actions = upgrade.upgrade(SEEDS_EN)

    assert edited.read_text() == mine  # the edited note is untouched, byte for byte
    assert any(a.startswith("kept your edit of data-engineer/nulls") for a in actions)
    assert knowledge.proposals()["data-engineer/nulls"] == SEEDS_EN["data-engineer"][1]["text"]
    assert _note("data-engineer/merge")["text"] == SEEDS_EN["data-engineer"][0]["text"]  # never edited: follows upstream
    assert {n["seed_id"]: n["id"] for n in knowledge.load_knowledge()} == before  # same ids, same notes, no duplicates
    again = [a for a in upgrade.upgrade(SEEDS_EN) if not a.startswith("backed up")]
    assert edited.read_text() == mine and len(knowledge.load_knowledge()) == 2  # the next upgrade still keeps it
    assert all(a.startswith("kept your edit of data-engineer/nulls") for a in again)  # only the review reminder


def test_bug_untouched_seed_resaved_in_nfd_counted_as_a_user_edit(home):
    """Bug: an editor that saves decomposed Unicode (NFD) made an untouched Vietnamese seed look edited, so it
    never followed upstream wording again."""
    import unicodedata
    from open_skill import upgrade
    seeds = {"data-engineer": [SEEDS_VI["data-engineer"][0]]}
    knowledge.init({"roles": {"data-engineer": 1.0}}, seeds=seeds)
    p = next((home / "knowledge").glob("*.md"))
    p.write_text(unicodedata.normalize("NFD", p.read_text()))
    actions = upgrade.upgrade({"data-engineer": [SEEDS_EN["data-engineer"][0]]})
    assert "updated data-engineer/merge (you had not edited it)" in actions
    assert _note("data-engineer/merge")["text"] == SEEDS_EN["data-engineer"][0]["text"]
