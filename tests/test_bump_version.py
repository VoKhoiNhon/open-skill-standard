import importlib.util
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("bump_version", ROOT / "scripts" / "bump_version.py")
bv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bv)


def copy_tree(tmp_path):
    for rel in ["pyproject.toml", "cli/open_skill/__init__.py", ".claude-plugin/plugin.json",
                "registry/adapters/open-skill.yaml", "README.md", "README.vi.md", "skills"]:
        src, dst = ROOT / rel, tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy(src, dst)
    return tmp_path


def test_bump_sets_every_version_and_pins_skills(tmp_path):
    root = copy_tree(tmp_path)
    changed = bv.bump(root, "9.8.7")
    assert 'version = "9.8.7"' in (root / "pyproject.toml").read_text(encoding="utf-8")
    assert '__version__ = "9.8.7"' in (root / "cli/open_skill/__init__.py").read_text(encoding="utf-8")
    assert '"version": "9.8.7"' in (root / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    router = (root / "skills/open-skill-router/SKILL.md").read_text(encoding="utf-8")
    assert "open-skill-standard@v9.8.7 open-skill" in router
    assert "skills/open-skill-router/SKILL.md" in changed
    assert bv.bump(root, "9.8.7") == []


def test_pin_replaces_existing_refs():
    text = "uvx --from git+https://github.com/VoKhoiNhon/open-skill-standard@v0.1.0 open-skill init"
    assert bv.pin(text, "0.2.0").count("@v0.2.0") == 1


def test_rejects_non_semver(tmp_path):
    with pytest.raises(ValueError):
        bv.bump(copy_tree(tmp_path), "v1")


def test_bump_keeps_lf_line_endings(tmp_path):
    root = copy_tree(tmp_path)
    changed = bv.bump(root, "9.8.7")
    assert changed
    for rel in changed:
        assert b"\r\n" not in (root / rel).read_bytes(), rel  # Windows would write CRLF
