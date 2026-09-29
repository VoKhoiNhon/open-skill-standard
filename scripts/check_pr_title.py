"""Fail unless a pull request title follows Conventional Commits: type(scope)!: summary."""

import re
import sys

TYPES = ("feat", "fix", "docs", "refactor", "test", "build", "ci", "chore", "perf", "style", "revert", "release")
PATTERN = re.compile(rf"^({'|'.join(TYPES)})(\([a-z0-9./-]+\))?!?: \S.*$")


def ok(title: str) -> bool:
    return bool(PATTERN.match(title.strip()))


if __name__ == "__main__":
    title = " ".join(sys.argv[1:])
    if ok(title):
        sys.exit(0)
    print(f"PR title must look like 'type(scope): summary' with type in {', '.join(TYPES)}; got: {title!r}")
    sys.exit(1)
