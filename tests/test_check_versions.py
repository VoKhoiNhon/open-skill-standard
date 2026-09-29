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
    p.write_text(p.read_text().replace('"version": "', '"version": "9', 1))
    assert cv.main(str(tmp_path)) == 1
    assert "versions disagree" in capsys.readouterr().out


cl = load("changelog")


def test_changelog_section_extraction():
    text = (ROOT / "CHANGELOG.md").read_text()
    body = cl.section(text, "0.2.0")
    assert "Safe upgrades" in body and "## [" not in body
    import pytest
    with pytest.raises(KeyError):
        cl.section(text, "9.9.9")


pt = load("check_pr_title")


def test_pr_titles():
    for good in ["feat: add x", "fix(lint): y", "release: v0.3.0 — spec", "feat(registry)!: rename z", "docs(vi): ghi chú"]:
        assert pt.ok(good), good
    for bad in ["Add x", "feat:missing space", "feature: x", "feat(Scope): x", "fix: "]:
        assert not pt.ok(bad), bad


cw = load("check_wheel")


def test_wheel_check(tmp_path):
    import zipfile
    w = tmp_path / "x.whl"
    with zipfile.ZipFile(w, "w") as z:
        for r in cw.REQUIRED[:-1]:
            z.writestr(r, "x")
    assert cw.missing(str(w)) == [cw.REQUIRED[-1]]
