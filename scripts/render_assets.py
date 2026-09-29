"""Regenerate the README images in .github/assets/ from the code, the registry and real CLI output.

    uv run python scripts/render_assets.py           # write every generated SVG
    uv run python scripts/render_assets.py --check   # exit 1 when a generated SVG is missing or stale (CI)

Diagrams come in a light and a -dark variant for <picture>. Output is deterministic: no timestamps, sorted data.
Uses only the standard library and this repository's own package.
"""

import argparse
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / ".github" / "assets"
sys.path.insert(0, str(ROOT / "cli"))
from open_skill import registry  # noqa: E402

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
# GitHub's own light and dark palettes, so the images sit naturally on either theme.
THEMES = {
    "light": {"text": "#1f2328", "muted": "#59636e", "box": "#f6f8fa", "line": "#d1d9e0",
              "blue": "#0969da", "blue-bg": "#ddf4ff", "green": "#1a7f37", "green-bg": "#dafbe1",
              "orange": "#bc4c00", "orange-bg": "#fff1e5", "purple": "#8250df", "purple-bg": "#fbefff",
              "red": "#cf222e", "red-bg": "#ffebe9"},
    "dark": {"text": "#e6edf3", "muted": "#9198a1", "box": "#151b23", "line": "#3d444d",
             "blue": "#4493f8", "blue-bg": "#0f2542", "green": "#3fb950", "green-bg": "#11281a",
             "orange": "#db6d28", "orange-bg": "#2e1c10", "purple": "#ab7df8", "purple-bg": "#241a38",
             "red": "#f85149", "red-bg": "#3a1716"},
}
ACCENTS = ("blue", "green", "orange", "purple", "red")


def _style(t: dict) -> str:
    rules = [f"text{{font-family:{SANS};font-size:13px;fill:{t['text']}}}",
             f".m{{fill:{t['muted']}}}", ".b{font-weight:600}", ".s{font-size:11.5px}", ".h{font-size:15px;font-weight:600}",
             f".mono{{font-family:{MONO};font-size:12px}}",
             f".box{{fill:{t['box']};stroke:{t['line']};stroke-width:1}}",
             f".dash{{fill:none;stroke:{t['line']};stroke-width:1;stroke-dasharray:4 3}}",
             f".edge{{fill:none;stroke:{t['muted']};stroke-width:1.4}}"]
    for a in ACCENTS:
        rules += [f".{a}{{fill:{t[a + '-bg']};stroke:{t[a]};stroke-width:1.2}}", f".t-{a}{{fill:{t[a]}}}",
                  f".e-{a}{{fill:none;stroke:{t[a]}}}", f"#arrow-{a} path{{fill:{t[a]}}}"]
    rules.append(f"#arrow path{{fill:{t['muted']}}}")
    return "".join(rules)


def svg(w: int, h: int, body: list[str], theme: str, label: str) -> str:
    marks = "".join(f'<marker id="arrow{s}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
                    f'markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z"/></marker>'
                    for s in ["", *(f"-{a}" for a in ACCENTS)])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(label, {chr(34): "&quot;"})}">\n'
            f"<style>{_style(THEMES[theme])}</style>\n<defs>{marks}</defs>\n" + "\n".join(body) + "\n</svg>\n")


def text(x, y, s, cls="", anchor="start") -> str:
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    c = f' class="{cls}"' if cls else ""
    return f'<text x="{x:g}" y="{y:g}"{c}{a}>{escape(str(s))}</text>'


def rect(x, y, w, h, cls="box", r=6) -> str:
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{r}" class="{cls}"/>'


def curve(x1, y1, x2, y2, cls="edge", width=None, arrow=None) -> str:
    """A horizontal S-curve from (x1, y1) to (x2, y2)."""
    mid = (x1 + x2) / 2
    sw = f' stroke-width="{width:.2g}"' if width else ""
    end = f' marker-end="url(#arrow{"-" + arrow if arrow and arrow != "muted" else ""})"' if arrow else ""
    return f'<path d="M{x1:g} {y1:g}C{mid:g} {y1:g} {mid:g} {y2:g} {x2:g} {y2:g}" class="{cls}"{sw}{end}/>'


def themed(name: str, draw) -> dict[str, str]:
    """name.svg (light) and name-dark.svg from draw(theme) -> svg text."""
    return {f"{name}.svg": draw("light"), f"{name}-dark.svg": draw("dark")}


def footer(w: int, y: int, source: str) -> str:
    return text(w - 16, y, f"generated from {source} by scripts/render_assets.py", "m s", "end")


# --- lifecycle: phases and artifacts from spec/taxonomy.yaml, edges from the adapters' produces/consumes ---

def lifecycle_edges(reg) -> tuple[dict, dict, dict]:
    """(phase, artifact) -> skills that act in the phase and produce the artifact; (artifact, phase) -> consumers;
    phase -> number of skills acting in it."""
    produced, consumed, per_phase = {}, {}, {}
    for s in reg.skills.values():
        for ph in s.get("phases", []):
            per_phase[ph] = per_phase.get(ph, 0) + 1
            for a in s.get("produces", []):
                produced[(ph, a)] = produced.get((ph, a), 0) + 1
            for a in s.get("consumes", []):
                consumed[(a, ph)] = consumed.get((a, ph), 0) + 1
    return produced, consumed, per_phase


def lifecycle(reg) -> dict[str, str]:
    phases = [p["id"] for p in reg.taxonomy["phases"]]
    artifacts = list(reg.taxonomy["artifacts"])
    produced, consumed, per_phase = lifecycle_edges(reg)
    w, top, row = 960, 78, 30
    h = top + row * len(artifacts) + 76
    pgap = row * (len(artifacts) - 1) / (len(phases) - 1)
    py = {p: top + i * pgap for i, p in enumerate(phases)}
    ay = {a: top + i * row for i, a in enumerate(artifacts)}
    lx, mx, rx, bw, aw = 40, 395, 750, 170, 170
    linked = {a for _, a in produced} | {a for a, _ in consumed}

    def draw(theme):
        b = [text(lx, 36, "Produced in phase", "h"), text(mx + aw / 2, 36, f"Artifact ({len(artifacts)})", "h", "middle"),
             text(rx + bw, 36, "Consumed in phase", "h", "end"),
             text(lx, 54, "a skill acting in the phase writes it", "m s"),
             text(rx + bw, 54, "a skill acting in the phase reads it", "m s", "end")]
        for (p, a), n in sorted(produced.items()):
            b.append(curve(lx + bw, py[p], mx, ay[a], "e-blue", 0.9 + 0.9 * math.sqrt(n), "blue"))
        for (a, p), n in sorted(consumed.items()):
            b.append(curve(mx + aw, ay[a], rx, py[p], "e-orange", 0.9 + 0.9 * math.sqrt(n), "orange"))
        for side, x, cls in (("l", lx, "blue"), ("r", rx, "orange")):
            for i, p in enumerate(phases):
                b += [rect(x, py[p] - 14, bw, 28, cls), text(x + 12, py[p] + 4.5, f"{i + 1}. {p}", "b"),
                      text(x + bw - 10, py[p] + 4.5, f"{per_phase.get(p, 0)} skills", "m s", "end")]
        for a in artifacts:
            b += [rect(mx, ay[a] - 11, aw, 22, "box" if a in linked else "dash", 11),
                  text(mx + aw / 2, ay[a] + 4.5, a, "" if a in linked else "m", "middle")]
        y = top + row * (len(artifacts) - 1) + 44
        b += [curve(lx, y, lx + 34, y, "e-blue", 2, "blue"), text(lx + 44, y + 4.5, "produces", "s"),
              curve(lx + 130, y, lx + 164, y, "e-orange", 2, "orange"), text(lx + 174, y + 4.5, "consumes", "s"),
              text(lx + 250, y + 4.5, "line width grows with the number of skills", "m s"),
              rect(lx + 540, y - 9, 34, 18, "dash", 9),
              text(lx + 584, y + 4.5, "found in repository files only; no skill writes or reads it", "m s"),
              footer(w, h - 12, "spec/taxonomy.yaml and registry/adapters")]
        return svg(w, h, b, theme, f"Lifecycle graph: the {len(phases)} phases and {len(artifacts)} artifacts of the "
                   "taxonomy, with the artifacts skills in each phase produce and consume")
    return themed("lifecycle", draw)


def render() -> dict[str, str]:
    reg = registry.load(ROOT)
    out = {}
    out.update(lifecycle(reg))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail when a generated file is missing or stale")
    args = ap.parse_args(argv)
    stale = []
    for name, content in render().items():
        path = ASSETS / name
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        if args.check:
            stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"wrote {name}")
    if stale:
        print("stale or missing: " + ", ".join(stale) + "\nrun: uv run python scripts/render_assets.py", file=sys.stderr)
        return 1
    if args.check:
        print("assets: up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
