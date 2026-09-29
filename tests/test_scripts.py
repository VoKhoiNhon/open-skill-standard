"""Table-driven tests for the small CI scripts: PR titles, CHANGELOG sections and wheel contents."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


title = load("check_pr_title")

PR_TITLES = [
    ("feat: add a thing", True),
    ("fix(lint): check every rule", True),
    ("feat(api)!: drop the v1 endpoints", True),
    ("release: v0.7.0", True),
    ("docs(readme.vi): sync", True),
    ('Revert "feat(route): phase flag"', True),     # the title GitHub's Revert button writes
    ("revert: feat(route): phase flag", True),
    ("Fix: capitalised type", False),                # lowercase by this repository's convention
    ("fix(Open_Skill): scope with capitals and _", False),
    ("feat:missing space", False),
    ("feat: ", False),
    ("feature: not a type", False),
    ("fix(): empty scope", False),
    ("Update README.md", False),
    ("", False),
]


@pytest.mark.parametrize("text,ok", PR_TITLES)
def test_pr_title(text, ok):
    assert title.ok(text) is ok
