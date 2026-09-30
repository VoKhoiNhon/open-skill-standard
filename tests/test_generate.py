import sqlite3
from contextlib import closing

from open_skill import generate, registry


def test_check_reports_a_stale_search_index(tmp_path):
    # Bug: `build --check` compared text outputs only, so the shipped dist/index.db went stale unnoticed.
    reg = registry.load()
    generate.write_all(reg, tmp_path)
    assert generate.stale(reg, tmp_path) == []
    db = tmp_path / "dist" / "index.db"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("UPDATE skills SET text = 'old words' WHERE rowid = 1")
        conn.commit()
    assert generate.stale(reg, tmp_path) == [db]
    db.unlink()
    assert generate.stale(reg, tmp_path) == [db]


def test_generated_files_use_lf_on_every_platform(tmp_path):
    # Bug: on Windows, write_text turned every newline into CRLF, so `build` rewrote dist/ and the playbooks in full.
    written = generate.write_all(registry.load(), tmp_path)
    assert written and all(b"\r\n" not in p.read_bytes() for p in written)
