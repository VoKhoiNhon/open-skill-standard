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


cl = load("changelog")
LOG = """# Changelog

## [Unreleased]

## [0.2.0] - 2026-01-02

Routing by role: the router reads role packs.

### Added
- b

## [0.1.0] - 2026-01-01

GitHub releases for every tag.

- a

[Unreleased]: https://example.org/compare/v0.2.0...HEAD
[0.2.0]: https://example.org/compare/v0.1.0...v0.2.0
[0.1.0]: https://example.org/releases/tag/v0.1.0
"""


@pytest.mark.parametrize("version,has,lacks", [
    ("0.2.0", ["Routing by role", "- b"], ["## [", "- a"]),
    ("0.1.0", ["GitHub releases", "- a"], ["[0.1.0]:", "[Unreleased]:"]),   # the link references are not notes
])
def test_changelog_section(version, has, lacks):
    body = cl.section(LOG, version)
    assert all(h in body for h in has) and not any(x in body for x in lacks)


@pytest.mark.parametrize("version,expected", [
    ("0.2.0", "v0.2.0 — routing by role"),
    ("0.1.0", "v0.1.0 — GitHub releases for every tag"),   # a brand keeps its capitals
])
def test_changelog_title(version, expected):
    assert cl.title(LOG, version) == expected


def test_changelog_missing_section():
    with pytest.raises(KeyError):
        cl.section(LOG, "9.9.9")


wheel = load("check_wheel")


def test_wheel_must_carry_every_tracked_data_file(tmp_path):
    # The hand-written list named 9 files; a wheel without evals/triggers/ or three of the four core skills passed.
    import zipfile
    need = wheel.required(ROOT)
    assert "open_skill/_data/evals/triggers/open-skill-router.yaml" in need
    assert "open_skill/_data/skills/open-skill-learn/SKILL.md" in need and "open_skill/route.py" in need
    gone = "open_skill/_data/evals/triggers/open-skill-router.yaml"
    with zipfile.ZipFile(tmp_path / "x.whl", "w") as z:
        for name in need:
            if name != gone:
                z.writestr(name, "")
    assert wheel.missing(str(tmp_path / "x.whl"), ROOT) == [gone]
