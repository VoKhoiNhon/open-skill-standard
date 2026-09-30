"""The GitHub Pages site: both languages match, every local reference resolves, the build is clean."""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
PAGES = {"en": REPO / "site" / "index.html", "vi": REPO / "site" / "vi" / "index.html"}
GENERATED = {"graph.html"}  # written by scripts/build_site.py, not kept in site/


def _images(html: str) -> list[str]:
    return [Path(p).name for p in re.findall(r'<(?:img [^>]*src|source [^>]*srcset)="([^"]+)"', html)]


def test_both_languages_show_the_same_images_in_the_same_order():
    en, vi = (_images(p.read_text(encoding="utf-8")) for p in PAGES.values())
    assert en and en == vi


def test_every_image_exists_and_every_img_tag_is_well_formed_with_alt_and_size():
    for page in PAGES.values():
        html = page.read_text(encoding="utf-8")
        for name in _images(html):
            assert (REPO / ".github" / "assets" / name).is_file(), f"{page}: missing asset {name}"
        for tag in re.findall(r"<img [^>]*>", html):
            assert re.fullmatch(r'<img(?: [a-z-]+="[^"]*")+>', tag), f"{page}: malformed {tag[:80]}"
            assert re.search(r'alt="[^"]+"', tag) and 'width="' in tag and 'height="' in tag, tag[:80]


def test_local_links_resolve_in_the_built_site():
    for page in PAGES.values():
        for ref in re.findall(r'(?:href|src|srcset)="([^"#]+)"', page.read_text(encoding="utf-8")):
            if re.match(r"[a-z]+:", ref):
                continue
            target = (page.parent / ref).resolve()
            rel = target.relative_to((REPO / "site").resolve()).as_posix()
            if rel in GENERATED:
                continue
            if rel.startswith("assets/"):
                target = REPO / ".github" / rel
            if target.is_dir():
                target = target / "index.html"
            assert target.is_file(), f"{page}: {ref} does not resolve"


def test_build_writes_pages_assets_and_a_graph_without_the_builders_installs(tmp_path):
    out = tmp_path / "site"
    subprocess.run([sys.executable, str(REPO / "scripts" / "build_site.py"), str(out)], check=True,
                   capture_output=True, text=True)
    assert (out / "index.html").is_file() and (out / "vi" / "index.html").is_file() and (out / ".nojekyll").exists()
    assert (out / "assets" / "sessions.svg").is_file()
    graph = (out / "graph.html").read_text(encoding="utf-8")
    assert '"installed": true' not in graph and '"installed":true' not in graph


def test_the_site_version_pin_is_checked_with_every_other_one():
    sys.path.insert(0, str(REPO / "scripts"))
    from check_versions import versions
    found = versions(REPO)
    pins = [k for k in found if k.startswith("site/")]
    assert pins and len(set(found.values())) == 1


def test_build_with_a_relative_out_dir_still_writes_the_graph(tmp_path):
    # CI runs `build_site.py _site`; the graph step runs in a temporary home, so the path must not stay relative.
    subprocess.run([sys.executable, str(REPO / "scripts" / "build_site.py"), "_site"], cwd=tmp_path, check=True,
                   capture_output=True, text=True)
    assert (tmp_path / "_site" / "graph.html").is_file()
