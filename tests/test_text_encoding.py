"""Every text file the CLI, scripts and tests read or write names its encoding; the locale default is cp1252 on Windows."""

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SOURCES = sorted([*(REPO / "cli" / "open_skill").glob("*.py"), *(REPO / "scripts").glob("*.py"),
                  *(REPO / "tests").glob("*.py")])


def _mode(call: ast.Call, index: int) -> str:
    """The mode argument of open() / Path.open(), "r" when absent or not a literal."""
    if len(call.args) > index and isinstance(call.args[index], ast.Constant):
        return str(call.args[index].value)
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return "r"


def unnamed_encodings(path: Path) -> list[str]:
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call) or any(kw.arg == "encoding" for kw in node.keywords):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
        if (name == "read_text" and not node.args) or (name == "write_text" and len(node.args) < 2):
            out.append(f"{path.name}:{node.lineno} {name}")
        elif name == "open" and isinstance(f, ast.Attribute) and "b" not in _mode(node, 0):
            out.append(f"{path.name}:{node.lineno} .open")
        elif name == "open" and isinstance(f, ast.Name) and len(node.args) > 0 and "b" not in _mode(node, 1):
            out.append(f"{path.name}:{node.lineno} open")
    return out


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_text_io_names_its_encoding(path):
    assert unnamed_encodings(path) == []


def locale_decoded(path: Path) -> list[str]:
    """subprocess calls with text=True and no encoding decode the child's output with the locale code page."""
    return [f"{path.name}:{node.lineno}" for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.Call) and not any(kw.arg == "encoding" for kw in node.keywords)
            and any(kw.arg in ("text", "universal_newlines") and getattr(kw.value, "value", None) is True
                    for kw in node.keywords)]


@pytest.mark.parametrize("path", [p for p in SOURCES if p.parent.name != "tests"], ids=lambda p: p.name)
def test_child_output_is_decoded_as_utf8(path):
    # git, graphify and agent CLIs print UTF-8 paths and text; cp1252 garbles them on Windows
    assert locale_decoded(path) == []
