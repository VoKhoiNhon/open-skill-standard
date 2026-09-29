import pytest

from open_skill import lint

HEAD = "---\nname: {name}\ndescription: {desc}\n---\n"


def doc(body, name="good-skill", desc="Does a thing. Use when the user asks for the thing."):
    return HEAD.format(name=name, desc=desc) + body


def rules(text):
    return [f.rule for f in lint.lint_text(text)]


def test_clean_skill_has_no_findings():
    assert rules(doc("Read the spec first, because the plan depends on it.\n")) == []


@pytest.mark.parametrize("text,rule", [
    (doc("x", name="Claude-Helper"), "frontmatter-name"),
    (doc("x", name="a" * 65), "frontmatter-name"),
    (doc("x", desc="a" * 1025), "frontmatter-description"),
    (doc("x", desc="uses <tags>"), "frontmatter-description"),
    ("---\nname: x\n---\nbody", "frontmatter-description"),
    (doc("\n" * 501), "length"),
    (doc("Show your reasoning in the response before answering."), "reasoning-in-response"),
    (doc("Double-check your answer before replying."), "redundant-verification"),
    (doc("Run this on claude-opus-5 for best results."), "hardcoded-model"),
    (doc("Set temperature: 0.2 for stability."), "legacy-params"),
    (doc("Only report high-severity issues.", name="code-review-pass", desc="Review code"), "review-filtering"),
    (doc("MUST a\nMUST b\nNEVER c\nALWAYS d\nCRITICAL e\nIMPORTANT f\n"), "shouting"),
])
def test_each_rule_triggers(text, rule):
    assert rule in rules(text)


def test_review_filter_only_applies_to_review_skills():
    assert "review-filtering" not in rules(doc("Only report high-severity issues."))


def test_every_finding_cites_a_source():
    for f in lint.lint_text(doc("Double-check your work. Use budget_tokens.")):
        assert f.source.startswith("https://")


def test_findings_carry_severity():
    by_rule = {f.rule: f.severity for f in lint.lint_text(doc("Show your reasoning in the response. Double-check your answer."))}
    assert by_rule == {"reasoning-in-response": "error", "redundant-verification": "warning"}


@pytest.mark.parametrize("name", ["-pdf", "pdf-", "pdf--processing", "PDF-Processing", "pdf_processing"])
def test_spec_name_rules(name):
    assert "frontmatter-name" in rules(doc("x", name=name))


def test_spec_name_accepts_valid_names():
    for name in ["pdf-processing", "data-analysis", "code-review", "a1"]:
        assert "frontmatter-name" not in rules(doc("x", name=name))
