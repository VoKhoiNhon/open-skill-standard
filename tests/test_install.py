from pathlib import Path

import pytest

from open_skill import install

REPO = Path(__file__).parents[1]


def skill(folder: Path, name: str, body: str = "Body.\n") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: A demo skill.\n---\n\n{body}")
    return folder


def test_core_skill_resolves_by_name():
    src = install.resolve_source("open-skill-router")
    assert src.kind == "core" and src.name == "open-skill-router"
    assert src.path == REPO / "skills" / "open-skill-router"


def test_local_folder_resolves_by_path(tmp_path):
    src = install.resolve_source(str(skill(tmp_path / "my-skill", "my-skill")))
    assert src.kind == "local" and src.name == "my-skill" and src.path == (tmp_path / "my-skill").resolve()


def test_unknown_source_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="core skill"):
        install.resolve_source("no-such-skill")
    with pytest.raises(ValueError):
        install.resolve_source(str(tmp_path))  # a folder without SKILL.md


@pytest.mark.parametrize("bad", ["../escape", "Upper", "a/b", "-dash"])
def test_unsafe_skill_names_are_rejected(tmp_path, bad):
    with pytest.raises(ValueError, match="name"):
        install.resolve_source(str(skill(tmp_path / "s", bad or '""')))
