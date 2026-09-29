from pathlib import Path

import pytest

from open_skill import models, registry

FIX = Path(__file__).parent / "fixtures"
PROFILES = registry.load(FIX / "repo").models


def test_exact_match_merges_inheritance_chain():
    p = models.resolve("claude-opus-5-5", PROFILES)
    assert p["id"] == "claude-opus-5-5"
    assert p["lineage"] == ["generic", "claude-opus-5", "claude-opus-5-5"]
    assert p["effort"] == {"small": "low", "medium": "medium", "large": "xhigh"}
    assert p["traits"]["self_verifies"] is True
    assert p["addenda"].count("Deliver what was asked, at the scope intended.") == 1
    assert p["addenda"][0] == "When you have enough information to act, act."
    assert set(p["avoid"]) == {"reasoning_in_response", "explicit_double_check"}
    assert p["chain"]["max_steps"] == 8


def test_normalizes_suffixes():
    assert models.resolve("Claude-Opus-5-5[1m]", PROFILES)["id"] == "claude-opus-5-5"
    assert models.resolve("claude-opus-5-5-20260901", PROFILES)["id"] == "claude-opus-5-5"


def test_unknown_future_model_falls_back_to_family():
    p = models.resolve("claude-opus-9", PROFILES)
    assert p["id"] == "claude-opus-5-5"
    assert p["matched_by"] == "family"


def test_unknown_or_missing_model_is_generic():
    assert models.resolve(None, PROFILES)["id"] == "generic"
    assert models.resolve("gpt-x", PROFILES)["id"] == "generic"


def test_inheritance_cycle_raises():
    profiles = {"a": {"id": "a", "match": ["a"], "inherits": "b"}, "b": {"id": "b", "match": ["b"], "inherits": "a"},
                "generic": {"id": "generic", "match": ["*"]}}
    with pytest.raises(ValueError):
        models.resolve("a", profiles)
