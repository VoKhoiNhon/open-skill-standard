import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("release_check", ROOT / "scripts" / "release_check.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

CHANGELOG = """# Changelog

## [Unreleased]

## [1.1.0] - 2026-10-01

Theme.

## [1.0.0] - 2026-09-01

First.

[Unreleased]: https://github.com/o/r/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/o/r/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/o/r/releases/tag/v1.0.0
"""


def test_current_release_passes():
    version = (ROOT / "cli/open_skill/__init__.py").read_text().split('"')[1]
    # Between releases main may hold [Unreleased] entries; everything else must already be in place.
    assert [p for p in rc.problems(ROOT, version) if not p.startswith("entries left under [Unreleased]")] == []


def test_version_not_bumped_everywhere(tmp_path):
    for rel in ["pyproject.toml", "cli/open_skill/__init__.py", ".claude-plugin/plugin.json",
                "registry/adapters/open-skill.yaml", "skills"]:
        src, dst = ROOT / rel, tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy(src, dst)
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG.replace("1.1.0", "9.9.9"))
    assert any("not bumped" in p for p in rc.problems(tmp_path, "9.9.9"))


def test_changelog_ok():
    assert rc.changelog_problems(CHANGELOG, "1.1.0") == []


def test_changelog_section_missing_or_undated():
    assert rc.changelog_problems(CHANGELOG, "1.2.0")[0].startswith("CHANGELOG has no section")
    undated = CHANGELOG.replace("## [1.1.0] - 2026-10-01", "## [1.1.0]")
    assert any("date" in p for p in rc.changelog_problems(undated, "1.1.0"))


def test_changelog_section_empty():
    empty = CHANGELOG.replace("Theme.\n", "")
    assert any("empty" in p for p in rc.changelog_problems(empty, "1.1.0"))


def test_compare_links_not_updated():
    stale = CHANGELOG.replace("compare/v1.1.0...HEAD", "compare/v1.0.0...HEAD")
    assert any("[Unreleased]" in p for p in rc.changelog_problems(stale, "1.1.0"))
    missing = CHANGELOG.replace("[1.1.0]: https://github.com/o/r/compare/v1.0.0...v1.1.0\n", "")
    assert any("[1.1.0]:" in p for p in rc.changelog_problems(missing, "1.1.0"))
    wrong_base = CHANGELOG.replace("compare/v1.0.0...v1.1.0", "compare/v0.9.0...v1.1.0")
    assert any("[1.1.0]:" in p for p in rc.changelog_problems(wrong_base, "1.1.0"))


def test_entries_left_under_unreleased():
    left = CHANGELOG.replace("## [Unreleased]\n", "## [Unreleased]\n\n### Added\n- z\n")
    assert any(p.startswith("entries left under [Unreleased]") for p in rc.changelog_problems(left, "1.1.0"))
