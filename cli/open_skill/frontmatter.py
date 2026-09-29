"""Parse the YAML frontmatter of a SKILL.md or knowledge file."""

import yaml


def split(text: str) -> tuple[dict, str]:
    """Return (frontmatter, body), or raise ValueError saying what is wrong with the frontmatter."""
    norm = text.removeprefix("\ufeff").replace("\r\n", "\n")
    if not norm.startswith("---\n"):
        raise ValueError("the file must start with a --- line and YAML frontmatter")
    end = norm.find("\n---", 3)  # from 3, so an empty block (---, ---) closes at once
    if end == -1:
        raise ValueError("the frontmatter has no closing --- line")
    try:
        meta = yaml.safe_load(norm[4:end]) if end > 3 else {}
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" at line {mark.line + 2}" if mark else ""  # +2: marks count from 0, after the opening ---
        raise ValueError(f"the frontmatter is not valid YAML{where}: {getattr(e, 'problem', None) or e}"
                         " (quote values that contain ': ')") from e
    if not isinstance(meta, dict):
        raise ValueError("the frontmatter must be a YAML mapping of fields")
    return meta, norm[end + 4 :].lstrip("\n")


def parse(text: str) -> tuple[dict, str]:
    """Return (frontmatter, body). Malformed or missing frontmatter yields ({}, text)."""
    try:
        return split(text)
    except ValueError:
        return {}, text


def text(meta: dict, key: str, default: str = "") -> str:
    """A field's value when it is a string, else default. Never str() other YAML values: an alias tree can be huge."""
    v = meta.get(key)
    return v if isinstance(v, str) else default
