"""Fail unless a pull request title follows Conventional Commits (type(scope)!: summary) or is a GitHub revert."""

import re
import sys

TYPES = ("feat", "fix", "docs", "refactor", "test", "build", "ci", "chore", "perf", "style", "revert", "release")
# Stricter than Conventional Commits on purpose: this repository writes types and scopes in lowercase.
PATTERN = re.compile(rf"^({'|'.join(TYPES)})(\([a-z0-9./-]+\))?!?: \S.*$")
GITHUB_REVERT = re.compile(r'^Revert ".+"$')  # the title GitHub's Revert button gives the pull request


def ok(title: str) -> bool:
    return bool(PATTERN.match(title.strip()) or GITHUB_REVERT.match(title.strip()))


if __name__ == "__main__":
    title = " ".join(sys.argv[1:])
    if ok(title):
        sys.exit(0)
    print(f"PR title must look like 'type(scope): summary' with type in {', '.join(TYPES)}; got: {title!r}")
    sys.exit(1)
