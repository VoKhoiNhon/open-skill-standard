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
