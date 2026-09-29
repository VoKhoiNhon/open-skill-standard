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
