"""Parse the YAML frontmatter of a SKILL.md or knowledge file."""

import yaml


def parse(text: str) -> tuple[dict, str]:
    """Return (frontmatter, body). Malformed or missing frontmatter yields ({}, text)."""
    norm = text.replace("\r\n", "\n")
    if not norm.startswith("---\n"):
        return {}, text
    end = norm.find("\n---", 4)
    if end == -1:
        return {}, text
    try:
        meta = yaml.safe_load(norm[4:end])
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    body = norm[end + 4 :].lstrip("\n")
    return meta, body
