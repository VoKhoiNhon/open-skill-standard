import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cv = load("check_versions")


def test_repository_versions_agree():
    assert cv.main(str(ROOT)) == 0


def test_disagreement_is_reported(tmp_path, capsys):
    for rel in ["pyproject.toml", "cli/open_skill/__init__.py", ".claude-plugin/plugin.json",
                "registry/adapters/open-skill.yaml", "skills"]:
        src, dst = ROOT / rel, tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy(src, dst)
    p = tmp_path / ".claude-plugin/plugin.json"
    p.write_text(p.read_text(encoding="utf-8").replace('"version": "', '"version": "9', 1), encoding="utf-8")
    assert cv.main(str(tmp_path)) == 1
    assert "versions disagree" in capsys.readouterr().out


cl = load("changelog")


def test_changelog_section_extraction():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    body = cl.section(text, "0.2.0")
    assert "Safe upgrades" in body and "## [" not in body
    import pytest
    with pytest.raises(KeyError):
        cl.section(text, "9.9.9")


def test_changelog_title_takes_the_theme_from_the_first_line():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert cl.title(text, "0.4.0") == "v0.4.0 — release engineering"
    assert cl.title(text, "0.1.0") == "v0.1.0 — first public release"
    assert cl.title("## [1.0.0] - x\n\nCI hardening.\n", "1.0.0") == "v1.0.0 — CI hardening"
    assert cl.title("## [1.0.0] - x\n\n### Added\n- y\n", "1.0.0") == "v1.0.0"


def test_changelog_missing_section_fails_with_one_clear_error(tmp_path):
    import subprocess
    import sys
    (tmp_path / "CHANGELOG.md").write_text("## [Unreleased]\n\n## [1.0.0] - x\n\nFirst.\n", encoding="utf-8")
    for args in (["v2.0.0"], ["title", "v2.0.0"]):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/changelog.py"), *args, str(tmp_path / "CHANGELOG.md")],
                           capture_output=True, text=True)
        assert r.returncode == 1 and r.stdout == ""
        assert r.stderr.startswith("::error::CHANGELOG.md has no section for 2.0.0") and "Traceback" not in r.stderr


pt = load("check_pr_title")


def test_pr_titles():
    for good in ["feat: add x", "fix(lint): y", "release: v0.3.0 — spec", "feat(registry)!: rename z", "docs(es): guía de instalación"]:
        assert pt.ok(good), good
    for bad in ["Add x", "feat:missing space", "feature: x", "feat(Scope): x", "fix: "]:
        assert not pt.ok(bad), bad




def _copy_versioned(tmp_path):
    for rel in ["pyproject.toml", "cli/open_skill/__init__.py", ".claude-plugin/plugin.json",
                "registry/adapters/open-skill.yaml", "skills"]:
        src, dst = ROOT / rel, tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy(src, dst)
    return tmp_path


def test_every_pin_in_a_skill_is_checked(tmp_path, capsys):
    # Only the last pin of a file was recorded, so an older pin before it went unnoticed.
    root = _copy_versioned(tmp_path)
    p = next((root / "skills").glob("*/SKILL.md"))
    good = cv.versions(root)["pyproject.toml"]
    p.write_text(p.read_text(encoding="utf-8") + f"\nold: uvx --from {cv.GIT_URL}@v0.0.1 open-skill\nnew: uvx --from {cv.GIT_URL}@v{good} open-skill\n", encoding="utf-8")
    assert cv.main(str(root)) == 1
    assert "0.0.1" in capsys.readouterr().out


def test_quoted_tested_version_is_read_as_its_value(tmp_path):
    root = _copy_versioned(tmp_path)
    p = root / "registry/adapters/open-skill.yaml"
    good = cv.versions(root)["pyproject.toml"]
    p.write_text(p.read_text(encoding="utf-8").replace(f"tested_version: {good}", f'tested_version: "{good}"'), encoding="utf-8")
    assert cv.main(str(root)) == 0


def test_readme_pins_are_checked_like_bump_version_writes_them(tmp_path, capsys):
    root = _copy_versioned(tmp_path)
    good = cv.versions(root)["pyproject.toml"]
    (root / "README.md").write_text(f"uvx --from {cv.GIT_URL}@v0.0.9 open-skill init\n", encoding="utf-8")
    (root / "README.vi.md").write_text(f"uvx --from {cv.GIT_URL}@v{good} open-skill init\n", encoding="utf-8")
    assert cv.main(str(root)) == 1
    assert "README.md" in capsys.readouterr().out


def test_a_missing_version_field_is_reported_not_a_traceback(tmp_path, capsys):
    root = _copy_versioned(tmp_path)
    p = root / "registry/adapters/open-skill.yaml"
    p.write_text("\n".join(line for line in p.read_text(encoding="utf-8").splitlines() if not line.startswith("tested_version")), encoding="utf-8")
    assert cv.main(str(root)) == 1
    assert "missing" in capsys.readouterr().out
