"""Corrupt and partial user data, hostile filesystems and scale: the CLI must fail clearly and never lose notes."""

import errno
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from open_skill import cli, knowledge, userdata

REPO = Path(__file__).parents[1]


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "h"
    monkeypatch.setenv("OPEN_SKILL_HOME", str(h))
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    monkeypatch.delenv("CLAUDECODE", raising=False)
    return h


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_truncated_events_log_is_read_up_to_the_damage(home, capsys):
    # A crash or a full disk mid-append leaves half a JSON line; every route used to fail on JSONDecodeError.
    knowledge.record({"type": "proposed", "route_id": "r-1", "task": "t", "chain": [{"id": "s/a", "invoke": "a"}]})
    knowledge.record({"type": "feedback", "route_id": "r-1", "ran": ["a"], "outcome": "ok"})
    with (home / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write('{"type": "proposed", "route_id": "r-2", "ta')
    assert knowledge.personal_weights()["s/a"] > 0
    assert cli.main(["route", "add tests", "--project", str(home.parent)]) == 0
    rid = json.loads(capsys.readouterr().out)["route_id"]
    assert knowledge.route_recorded(rid)  # the next event starts on its own line, not glued to the broken one
    lines = (home / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4 and all(lines)
    assert '"route_id": "r-2", "ta' in (home / "events.jsonl").read_text(encoding="utf-8")  # damage kept, not rewritten
