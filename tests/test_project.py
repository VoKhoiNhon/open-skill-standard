from pathlib import Path

from open_skill import project, registry

FIX = Path(__file__).parent / "fixtures"
REG = registry.load(FIX / "repo")


def inspect(p):
    return project.inspect(p, REG.taxonomy, REG.roles)


def make(tmp_path, *files):
    for f in files:
        p = tmp_path / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    return tmp_path


def test_native_framework_precedence(tmp_path):
    assert inspect(make(tmp_path, ".specify/memory/constitution.md"))["native"] == "spec-kit"
    make(tmp_path, "_bmad/config.toml")
    assert inspect(tmp_path)["native"] == "spec-kit"


def test_bmad_native(tmp_path):
    assert inspect(make(tmp_path, "_bmad/config.toml"))["native"] == "bmad-method"


def test_artifacts_and_codegraph(tmp_path):
    r = inspect(make(tmp_path, "specs/001-x/spec.md", "docs/adr/0001-db.md", ".codegraph/db", "tasks.md"))
    assert {"spec", "adr", "tasks"} <= set(r["artifacts"])
    assert r["codegraph"] is True


def test_role_signals_and_languages(tmp_path):
    r = inspect(make(tmp_path, "dbt_project.yml", "models/a.sql", "models/b.sql", "app.py", "node_modules/x/y.js"))
    assert r["role_signals"]["data-engineer"] > 0
    assert r["languages"][".sql"] == 2
    assert ".js" not in r["languages"]


def test_empty_project(tmp_path):
    r = inspect(tmp_path)
    assert r["native"] is None and r["artifacts"] == [] and r["codegraph"] is False
