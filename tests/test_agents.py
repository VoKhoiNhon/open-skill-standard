from pathlib import Path

from open_skill import agents

AGENT = {
    "id": "demo-agent",
    "global": [{"path": "~/.demo/skills"}, {"path": "~/.config/demo/skills"}],
    "project": [{"path": ".demo/skills"}],
    "relocate": [{"var": "DEMO_HOME", "replaces": "~/.demo"}, {"var": "XDG_CONFIG_HOME", "replaces": "~/.config"}],
}


def test_global_folders_expand_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DEMO_HOME", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert agents.folders(AGENT, "global") == [tmp_path / ".demo/skills", tmp_path / ".config/demo/skills"]


def test_relocation_env_var_replaces_prefix(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DEMO_HOME", str(tmp_path / "elsewhere"))
    monkeypatch.setenv("XDG_CONFIG_HOME", "")  # empty means unset
    assert agents.folders(AGENT, "global") == [tmp_path / "elsewhere/skills", tmp_path / ".config/demo/skills"]


def test_relocation_matches_whole_segments(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DEMO_HOME", str(tmp_path / "elsewhere"))
    assert agents.expand(AGENT, "~/.demo-other/skills") == tmp_path / ".demo-other/skills"


def test_project_folders_need_a_project(tmp_path):
    assert agents.folders(AGENT, "project") == []
    assert agents.folders(AGENT, "project", tmp_path) == [tmp_path.resolve() / ".demo/skills"]


def test_detected_when_any_detect_path_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    agent = {**AGENT, "detect": [{"path": "~/.demo"}, {"path": "~/.demo-alt"}]}
    monkeypatch.delenv("DEMO_HOME", raising=False)
    assert agents.detected(agent) is False
    (tmp_path / ".demo-alt").mkdir()
    assert agents.detected(agent) is True


def test_detected_follows_relocation(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "moved").mkdir()
    monkeypatch.setenv("DEMO_HOME", str(tmp_path / "moved"))
    assert agents.detected({**AGENT, "detect": [{"path": "~/.demo"}]}) is True


WALKER = {**AGENT, "walk_up": {"source": "https://example.com/docs"}}


def test_walk_up_reads_project_folders_up_to_the_repository_root(tmp_path):
    root = tmp_path / "outer" / "repo"
    (root / ".git").mkdir(parents=True)
    sub = root / "packages" / "web"
    sub.mkdir(parents=True)
    assert agents.folders(WALKER, "project", sub) == [
        sub.resolve() / ".demo/skills", (root / "packages").resolve() / ".demo/skills", root.resolve() / ".demo/skills"]
    assert agents.folders(AGENT, "project", sub) == [sub.resolve() / ".demo/skills"]  # only agents that walk up


def test_walk_up_stops_at_a_worktree_root(tmp_path):
    (tmp_path / ".git").mkdir()
    tree = tmp_path / "wt"
    tree.mkdir()
    (tree / ".git").write_text("gitdir: ../.git/worktrees/wt\n", encoding="utf-8")  # a linked worktree's .git is a file
    assert agents.folders(WALKER, "project", tree / "src") == [
        (tree / "src").resolve() / ".demo/skills", tree.resolve() / ".demo/skills"]


def test_walk_up_outside_a_repository_reads_only_the_project(tmp_path):
    assert agents.folders(WALKER, "project", tmp_path / "a" / "b") == [(tmp_path / "a/b").resolve() / ".demo/skills"]


def test_depth_defaults_to_one_level():
    assert agents.depth(AGENT) == 1
    assert agents.depth({**AGENT, "nested": {"depth": 5, "source": "https://example.com"}}) == 5


def test_antigravity_cli_reads_the_shared_project_folder(tmp_path, monkeypatch):
    # antigravity.google/docs/skills: workspace .agents/skills, global ~/.gemini/antigravity-cli/skills.
    from open_skill import paths, registry
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    a = registry.load(paths.data_root()).agents["antigravity-cli"]
    assert agents.folders(a, "global") == [tmp_path / ".gemini/antigravity-cli/skills"]
    assert agents.folders(a, "project", tmp_path / "p") == [(tmp_path / "p").resolve() / ".agents/skills"]
    assert not agents.detected(a)
    (tmp_path / ".gemini/antigravity-cli").mkdir(parents=True)
    assert agents.detected(a)
