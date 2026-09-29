import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("privacy_guard", ROOT / "scripts" / "privacy_guard.py")
pg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pg)


def _svg(tmp_path, body: str) -> str:
    p = tmp_path / ".github" / "assets" / "x.svg"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" aria-label="a capture">{body}</svg>\n')
    return ".github/assets/x.svg"


def test_email_in_svg_text_is_flagged(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = _svg(tmp_path, "<text>mail someone@example.com</text>")
    assert pg.check([f]) == [f"{f}: text looks like email"]


def test_local_home_path_in_a_capture_is_flagged(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = _svg(tmp_path, "<text>registry=/Users/alice/src/open-skill-standard</text>")
    assert pg.check([f]) == [f"{f}: text looks like local-path"]


def test_svg_geometry_is_not_scanned(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = _svg(tmp_path, '<path d="M210 94C302.5 94 302.5 184 395 184"/><text>score 2.5</text>')
    assert pg.check([f]) == []


def test_readme_home_path_is_flagged(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text("run it from /home/bob/work\n")
    assert pg.check(["README.md"]) == ["README.md:1: looks like local-path"]


def _repo(tmp_path, files: dict[str, str]):
    import subprocess
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    return tmp_path


def test_tracked_lists_names_with_spaces_and_accents(tmp_path):
    # `git ls-files` quotes non-ASCII names and split() broke names at spaces, so those files were never scanned.
    root = _repo(tmp_path, {"skills/tiếng việt/SKILL.md": "x", "skills/a b.md": "y", "README.md": "z"})
    assert sorted(pg.tracked(root)) == ["README.md", "skills/a b.md", "skills/tiếng việt/SKILL.md"]


def test_main_scans_from_the_repository_root(tmp_path, monkeypatch, capsys):
    # Run from a subfolder, paths no longer started with skills/ and nothing was scanned.
    root = _repo(tmp_path, {"skills/x/SKILL.md": "mail alice@corp.example\n"})
    monkeypatch.chdir(root / "skills")
    assert pg.main(root) == 1
    assert "skills/x/SKILL.md:1: looks like email" in capsys.readouterr().out
