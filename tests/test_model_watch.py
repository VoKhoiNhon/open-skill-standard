import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("model_watch", ROOT / "scripts" / "model_watch.py")
mw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mw)


def test_extracts_ids_from_guide_text():
    text = ("[Prompting Claude Fable 5.1](/docs/prompting-claude-fable-5-1) "
            "[Prompting Claude Opus 5](/docs/prompting-claude-opus-5) and a passing mention of Claude Opus 4.1.")
    assert mw.model_ids(text) == {"claude-fable-5-1", "claude-opus-5"}


def test_every_currently_listed_model_has_a_profile():
    profiles = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in (ROOT / "registry/models").glob("*.yaml")]
    listed = {"claude-fable-5-1", "claude-mythos-5-1", "claude-fable-5", "claude-mythos-5", "claude-opus-5-5",
              "claude-opus-5", "claude-opus-4-8", "claude-sonnet-5-5", "claude-sonnet-5", "claude-haiku-4-5"}
    assert mw.uncovered(listed, profiles) == []
    assert mw.uncovered({"claude-opus-9"}, profiles) == ["claude-opus-9"]
