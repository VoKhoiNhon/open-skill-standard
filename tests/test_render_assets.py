import importlib.util
import xml.dom.minidom
from pathlib import Path

from open_skill import registry

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("render_assets", ROOT / "scripts" / "render_assets.py")
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)


def test_lifecycle_edges_come_from_the_adapters():
    reg = registry.Registry(taxonomy={}, skills={
        "a/x": {"phases": ["plan", "build"], "produces": ["plan"], "consumes": ["spec"]},
        "a/y": {"phases": ["build"], "produces": ["code-change", "plan"]}})
    produced, consumed, per_phase = ra.lifecycle_edges(reg)
    assert produced == {("plan", "plan"): 1, ("build", "plan"): 2, ("build", "code-change"): 1}
    assert consumed == {("spec", "plan"): 1, ("spec", "build"): 1}
    assert per_phase == {"plan": 1, "build": 2}


def test_every_generated_svg_is_well_formed_with_alt_text():
    for name, content in ra.render().items():
        doc = xml.dom.minidom.parseString(content)
        assert doc.documentElement.getAttribute("aria-label"), name


def test_check_reports_a_stale_asset(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ra, "ASSETS", tmp_path)
    monkeypatch.setattr(ra, "render", lambda: {"a.svg": "<svg/>\n", "b.svg": "<svg/>\n"})
    assert ra.main([]) == 0
    assert ra.main(["--check"]) == 0
    stale = next(tmp_path.glob("*.svg"))
    stale.write_text("old", encoding="utf-8")
    assert ra.main(["--check"]) == 1
    assert stale.name in capsys.readouterr().err


def test_routing_diagram_uses_the_router_constants(monkeypatch):
    from open_skill import route
    monkeypatch.setattr(route, "MIN_SCORE", 0.42)
    monkeypatch.setattr(route, "FLOW_BONUS", 1.5)
    light = ra.pipeline()["routing.svg"]
    assert "below 0.42" in light and "× 1.5 if it consumes" in light


def test_mask_hides_temp_paths_route_ids_and_the_version(tmp_path):
    from open_skill import __version__
    real = tmp_path.resolve()
    out = ra._mask(f"open-skill {__version__}  home={real}/home/.open-skill\n"
                   f"== {real}/project/skill\nroute r-20260929-154255-da3162 in {ra.ROOT}/tests", tmp_path)
    assert out == "open-skill X.Y.Z  home=~/.open-skill\n== ./skill\nroute r-<id> in tests"


def test_wrap_keeps_every_line_within_the_terminal_width():
    long = "   runner-ups: " + ", ".join(f"source/skill-{i} 0.{i}" for i in range(30))
    parts = ra._wrap(long)
    assert len(parts) > 1 and all(len(p) <= ra.COLS for p in parts)
    assert all(p.startswith("     ") for p in parts[1:])
    assert " ".join(p.strip() for p in parts) == long.strip()
