"""Fail unless a built wheel carries the registry, spec and skills the CLI needs at run time."""

import sys
import zipfile

REQUIRED = [
    "open_skill/cli.py",
    "open_skill/_data/spec/taxonomy.yaml",
    "open_skill/_data/registry/roles/data-engineer.yaml",
    "open_skill/_data/registry/models/generic.yaml",
    "open_skill/_data/registry/adapters/superpowers.yaml",
    "open_skill/_data/registry/agents/claude-code.yaml",
    "open_skill/_data/skills/open-skill-router/SKILL.md",
    "open_skill/_data/evals/routing.yaml",
]


def missing(wheel: str) -> list[str]:
    names = set(zipfile.ZipFile(wheel).namelist())
    return [r for r in REQUIRED if r not in names]


if __name__ == "__main__":
    gaps = missing(sys.argv[1])
    for g in gaps:
        print(f"missing from wheel: {g}")
    sys.exit(1 if gaps else 0)
