"""Parse the YAML frontmatter of a SKILL.md or knowledge file."""

import yaml


def parse(text: str) -> tuple[dict, str]:
    """Return (frontmatter, body). Malformed or missing frontmatter yields ({}, text)."""
    norm = text.removeprefix("\ufeff").replace("\r\n", "\n")
    if not norm.startswith("---\n"):
        return {}, text
    end = norm.find("\n---", 3)  # from 3, so an empty block (---, ---) closes at once
    if end == -1:
        return {}, text
    try:
        meta = yaml.safe_load(norm[4:end]) if end > 3 else {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    body = norm[end + 4 :].lstrip("\n")
    return meta, body
