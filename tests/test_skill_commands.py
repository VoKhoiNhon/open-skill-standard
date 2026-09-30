"""Every `open-skill ...` command a skill tells the agent to run must parse with the real CLI parser."""

import argparse
import re
import shlex
from pathlib import Path

import pytest

from open_skill import cli

REPO = Path(__file__).parents[1]
DOCS = sorted((REPO / "skills").rglob("*.md"))


def commands(text: str) -> list[str]:
    """Inline `open-skill ...` spans and `open-skill ...` lines of fenced code blocks."""
    found = re.findall(r"`(open-skill [^`]+)`", text)
    for block in re.findall(r"^```[a-z]*\n(.*?)^```", text, re.M | re.S):
        found += [ln.strip() for ln in block.splitlines() if ln.strip().startswith("open-skill ")]
    return found


def _argv(command: str) -> list[str]:
    """Placeholders become a value, [optional] parts are kept, a|b choices take the first."""
    command = re.sub(r"<[^<>]+>", "X", command).replace("[", "").replace("]", "")
    return [tok.split("|")[0] for tok in shlex.split(command)[1:]]


class _Bad(Exception):
    pass


def problem(command: str) -> str | None:
    """None if the command parses; otherwise argparse's complaint. Naming a command alone is fine."""
    argv = _argv(command)

    def error(self, message):
        raise _Bad(message)

    old, argparse.ArgumentParser.error = argparse.ArgumentParser.error, error
    try:
        cli.build_parser().parse_args(argv)
    except _Bad as e:
        if len(argv) == 1 and "arguments are required" in str(e):
            return None
        if "invalid choice: 'X'" in str(e):  # a placeholder where the agent picks one of the choices
            return None
        return str(e)
    finally:
        argparse.ArgumentParser.error = old
    return None


CASES = list({c: (p.relative_to(REPO).as_posix(), c) for p in reversed(DOCS) for c in commands(p.read_text(encoding="utf-8"))}.values())


def test_the_skills_name_commands_at_all():
    assert len(CASES) >= 15 and {c.split()[1] for _, c in CASES} >= {"route", "feedback", "learn", "search"}


@pytest.mark.parametrize("doc,command", CASES, ids=[f"{d}::{c[:60]}" for d, c in CASES])
def test_skill_commands_parse_with_the_cli(doc, command):
    assert problem(command) is None, f"{doc}: `{command}` does not parse: {problem(command)}"


@pytest.mark.parametrize("command", [
    "open-skill route X --no-such-flag",
    "open-skill no-such-command",
    "open-skill feedback X --outcome maybe",
    "open-skill learn X --applies-to role:x --type opinion",
])
def test_the_check_catches_drift(command):
    assert problem(command)
