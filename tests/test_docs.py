import re
from pathlib import Path

from open_skill import registry

REPO = Path(__file__).parents[1]


def _agent_rows(readme: str) -> dict[str, tuple[str, str]]:
    rows = re.findall(r"^\|[^|]+\| `([a-z0-9-]+)` \| `([^`]+)` \| `([^`]+)` \|$", readme, re.M)
    return {aid: (g, p) for aid, g, p in rows}


def test_readme_agent_table_matches_the_registry():
    reg = registry.load()
    want = {aid: (a["global"][0]["path"], a["project"][0]["path"]) for aid, a in reg.agents.items()}
    for name in ("README.md", "README.vi.md"):
        assert _agent_rows((REPO / name).read_text(encoding="utf-8")) == want, f"{name}: update the agent table from registry/agents"


def test_router_skill_lists_the_taxonomy_phases_the_agent_passes():
    skill = (REPO / "skills" / "open-skill-router" / "SKILL.md").read_text(encoding="utf-8")
    assert "--phase" in skill and "--size" in skill
    listed = set(re.findall(r"`([a-z]+)` \(", skill))
    assert {p["id"] for p in registry.load().taxonomy["phases"]} <= listed, "list every phase id in the router skill"


def test_router_manual_path_follows_the_playbooks_build_window():
    # The manual fallback walked plan → build → verify → review for every role; eleven roles set a build_window.
    skill = (REPO / "skills" / "open-skill-router" / "SKILL.md").read_text(encoding="utf-8")
    manual = skill.split("## Without the CLI")[1]
    assert "Build tasks for this role walk" in manual and "done directly" in manual


# Letters only Vietnamese uses, plain and with tone marks; enough to spot Vietnamese text in files meant to be English.
VIETNAMESE = re.compile("[ăâđêôơư]|[aeiouy][̣̀́̃̉]"
                        "|[Ạ-ỹ]", re.I)


def test_skills_are_english_only():
    """Vietnamese requests find the skills through the registry's vi blocks (SPEC §3.1), not their text."""
    found = [f"{p.relative_to(REPO)}:{n}" for p in sorted((REPO / "skills").rglob("*.md"))
             for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if VIETNAMESE.search(line)]
    assert not found, found


def _vietnamese_outside_test_inputs(path: Path) -> list[str]:
    """file:line where Vietnamese appears in code, comments, docstrings or names; in tests/, strings are test inputs."""
    import tokenize
    with path.open("rb") as f:
        toks = list(tokenize.tokenize(f.readline))
    code = [t for t in toks if t.type not in (tokenize.COMMENT, tokenize.NL)]
    out = [t.start[0] for t in toks if t.type == tokenize.COMMENT and VIETNAMESE.search(t.string)]
    for i, tok in enumerate(code):
        before, after = code[i - 1].type if i else None, code[i + 1].type if i + 1 < len(code) else None
        docstring = tok.type == tokenize.STRING and before in (tokenize.INDENT, tokenize.NEWLINE, tokenize.ENCODING) \
            and after == tokenize.NEWLINE
        test_input = path.parent.name == "tests" and tok.type == tokenize.STRING and not docstring
        if VIETNAMESE.search(tok.string) and not test_input:
            out.append(tok.start[0])
    return [f"{path.relative_to(REPO)}:{n}" for n in sorted(set(out))]


def test_code_comments_and_test_names_are_english():
    """Vietnamese belongs in locale data (spec/taxonomy.yaml, registry vi blocks) and in test inputs, not in code."""
    files = [*sorted((REPO / "cli").rglob("*.py")), *sorted((REPO / "scripts").glob("*.py")), *sorted((REPO / "tests").glob("*.py"))]
    assert not [hit for p in files for hit in _vietnamese_outside_test_inputs(p)]


def _vietnamese_prose(path: Path) -> list[int]:
    """Lines with Vietnamese outside fenced code blocks and code spans, where examples of the vi locale belong."""
    out, fenced = [], False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and VIETNAMESE.search(re.sub(r"`[^`]*`", "", line)):
            out.append(n)
    return out


def test_spec_and_changelog_prose_is_english():
    for name in ("spec/SPEC.md", "CHANGELOG.md", "CONTRIBUTING.md"):
        assert not _vietnamese_prose(REPO / name), f"{name}: put Vietnamese examples in code spans"


def _structure(text: str) -> tuple[list[int], list[tuple[str, list[str]]]]:
    """Heading levels outside code, and each fenced block's language and lines without comments (comments and
    prose are translated; commands and output are not)."""
    levels, blocks, fence = [], [], None
    for line in text.splitlines():
        if line.startswith("```"):
            if fence is None:
                fence = (line[3:].strip(), [])
            else:
                blocks.append(fence)
                fence = None
        elif fence is not None:
            code = re.sub(r"\s+# .*$", "", line) if fence[0] == "bash" else line.rstrip()
            if code and not code.lstrip().startswith("#"):
                fence[1].append(code)
        elif re.match(r"#{1,6} ", line):
            levels.append(len(line.split()[0]))
    return levels, blocks


def test_vietnamese_readme_is_a_structural_translation():
    en, vi = (REPO / "README.md").read_text(encoding="utf-8"), (REPO / "README.vi.md").read_text(encoding="utf-8")
    (en_levels, en_blocks), (vi_levels, vi_blocks) = _structure(en), _structure(vi)
    assert vi_levels == en_levels, "README.vi.md needs the same sections as README.md"
    assert vi_blocks == en_blocks, "README.vi.md needs the same command and output blocks as README.md"
    assert "[Tiếng Việt](README.vi.md)" in en.split("\n## ")[0] and "[English](README.md)" in vi.split("\n## ")[0]


def _images(text: str) -> tuple[list[str], list[str]]:
    """Every image path in order (<img src> and <picture> <source srcset>), and the alt text of each <img>."""
    paths = re.findall(r'<(?:img [^>]*src|source [^>]*srcset)="([^"]+)"', text)
    alts = [(re.search(r'alt="([^"]*)"', tag) or [None, ""])[1] for tag in re.findall(r"<img [^>]*>", text)]
    return paths, alts


def test_readme_images_exist_have_alt_text_and_match_between_the_readmes():
    (en, en_alts), (vi, vi_alts) = (_images((REPO / n).read_text(encoding="utf-8")) for n in ("README.md", "README.vi.md"))
    for path in en + vi:
        assert path.startswith(".github/assets/") and (REPO / path).is_file(), f"missing image {path}"
    assert all(a.strip() for a in en_alts + vi_alts), "every <img> needs alt text"
    assert en == vi, "README.vi.md needs the same images in the same order as README.md"
