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
        assert _agent_rows((REPO / name).read_text()) == want, f"{name}: update the agent table from registry/agents"


def test_router_skill_lists_the_taxonomy_phases_the_agent_passes():
    skill = (REPO / "skills" / "open-skill-router" / "SKILL.md").read_text()
    assert "--phase" in skill and "--size" in skill
    listed = set(re.findall(r"`([a-z]+)` \(", skill))
    assert {p["id"] for p in registry.load().taxonomy["phases"]} <= listed, "list every phase id in the router skill"


def test_router_manual_path_follows_the_playbooks_build_window():
    # The manual fallback walked plan → build → verify → review for every role; eleven roles set a build_window.
    skill = (REPO / "skills" / "open-skill-router" / "SKILL.md").read_text()
    manual = skill.split("## Without the CLI")[1]
    assert "Build tasks for this role walk" in manual and "done directly" in manual


# Letters only Vietnamese uses, plain and with tone marks; enough to spot Vietnamese text in files meant to be English.
VIETNAMESE = re.compile("[ăâđêôơư]|[aeiouy][̣̀́̃̉]"
                        "|[Ạ-ỹ]", re.I)


def test_skills_are_english_only():
    """Vietnamese requests find the skills through the registry's vi blocks (SPEC §3.1), not their text."""
    found = [f"{p.relative_to(REPO)}:{n}" for p in sorted((REPO / "skills").rglob("*.md"))
             for n, line in enumerate(p.read_text().splitlines(), 1) if VIETNAMESE.search(line)]
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
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and VIETNAMESE.search(re.sub(r"`[^`]*`", "", line)):
            out.append(n)
    return out


def test_spec_and_changelog_prose_is_english():
    for name in ("spec/SPEC.md", "CHANGELOG.md", "CONTRIBUTING.md"):
        assert not _vietnamese_prose(REPO / name), f"{name}: put Vietnamese examples in code spans"
