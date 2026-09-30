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
    (doc("x", desc="uses <tags>"), "description-angle-brackets"),
    ("---\nname: x\n---\nbody", "frontmatter-description"),
    (doc("\n" * 501), "length"),
    (doc("Show your reasoning in the response before answering."), "reasoning-in-response"),
    (doc("Double-check your answer before replying."), "redundant-verification"),
    (doc("Run this on claude-opus-5 for best results."), "hardcoded-model"),
    (doc("Set temperature: 0.2 for stability."), "sampling-params"),
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


def test_name_must_match_folder(tmp_path):
    d = tmp_path / "pdf-tools"
    d.mkdir()
    (d / "SKILL.md").write_text(doc("x", name="pdf-processing"), encoding="utf-8")
    assert [f.rule for f in lint.lint_file(d / "SKILL.md")] == ["name-matches-folder"]
    (d / "SKILL.md").write_text(doc("x", name="pdf-tools"), encoding="utf-8")
    assert lint.lint_file(d / "SKILL.md") == []


def fm(extra: str, body: str = "x") -> str:
    return f"---\nname: good-skill\ndescription: Does a thing.\n{extra}\n---\n{body}"


@pytest.mark.parametrize("extra,rule", [
    ("compatibility: ''", "field-compatibility"),
    ("compatibility: " + "a" * 501, "field-compatibility"),
    ("metadata:\n  version: 1.0", "field-metadata"),
    ("metadata: [a, b]", "field-metadata"),
    ("allowed-tools: [Read, Bash]", "field-allowed-tools"),
    ("license: {name: MIT}", "field-license"),
])
def test_optional_field_rules(extra, rule):
    assert rule in rules(fm(extra))


def test_valid_optional_fields_pass():
    extra = "license: Apache-2.0\ncompatibility: Requires git and uv\nmetadata:\n  author: example-org\n  version: \"1.0\"\nallowed-tools: Bash(git:*) Read"
    assert rules(fm(extra)) == []


def test_unknown_fields_warn_but_agent_extensions_do_not():
    found = lint.lint_text(fm("descripton: typo\nwhen_to_use: when asked\nargument-hint: '[file]'"))
    assert [(f.rule, f.severity) for f in found] == [("unknown-field", "warning")]
    assert "descripton" in found[0].message


def test_missing_references_are_errors(tmp_path):
    d = tmp_path / "good-skill"
    (d / "references").mkdir(parents=True)
    (d / "references" / "guide.md").write_text("ok", encoding="utf-8")
    body = ("See [the guide](references/guide.md), [gone](references/gone.md), `scripts/run.py`, "
            "[web](https://x.org/a), [anchor](#top), `references/roles/<role>.md`.")
    (d / "SKILL.md").write_text(doc(body), encoding="utf-8")
    found = [(f.rule, f.message) for f in lint.lint_file(d / "SKILL.md")]
    assert [r for r, _ in found] == ["missing-reference", "missing-mention"]
    assert "references/gone.md" in found[0][1] and "scripts/run.py" in found[1][1]


def test_long_body_warns_on_tokens():
    found = lint.lint_text(doc("word " * 4200))
    assert ("body-tokens", "warning") in [(f.rule, f.severity) for f in found]
    assert "body-tokens" not in rules(doc("word " * 100))


def write_json(tmp_path, name, obj):
    import json
    p = tmp_path / ".claude-plugin" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj), encoding="utf-8")
    return p


def test_marketplace_required_fields(tmp_path):
    ok = {"name": "tools", "owner": {"name": "me"}, "plugins": [{"name": "a", "source": "./"}]}
    assert lint.lint_marketplace(write_json(tmp_path, "marketplace.json", ok)) == []
    bad = {"name": "tools", "plugins": [{"name": "a"}]}
    rules_found = [f.rule for f in lint.lint_marketplace(write_json(tmp_path, "marketplace.json", bad))]
    assert rules_found == ["marketplace-field", "marketplace-plugin"]
    assert [f.rule for f in lint.lint_marketplace(write_json(tmp_path, "marketplace.json", "{nope"))] == ["manifest-json"]


def test_repository_marketplace_is_valid():
    from pathlib import Path
    root = Path(__file__).parents[1]
    assert lint.lint_marketplace(root / ".claude-plugin" / "marketplace.json") == []


def test_marketplace_source_escape_and_impersonation(tmp_path):
    doc_ = {"name": "anthropic-official-tools", "owner": {"name": "x"}, "plugins": [{"name": "a", "source": "../elsewhere"}]}
    found = [(f.rule, f.severity) for f in lint.lint_marketplace(write_json(tmp_path, "marketplace.json", doc_))]
    assert found == [("marketplace-source", "error"), ("marketplace-reserved", "warning")]


def test_plugin_json_rules(tmp_path):
    assert lint.lint_plugin(write_json(tmp_path, "plugin.json", {"name": "tools", "version": "1.2.3", "description": "d"})) == []
    found = [f.rule for f in lint.lint_plugin(write_json(tmp_path, "plugin.json", {"name": "My Tools", "version": "v1"}))]
    assert found == ["plugin-name", "plugin-version", "plugin-description"]


def test_lint_paths_includes_manifests(tmp_path):
    write_json(tmp_path, "plugin.json", {"name": "Bad Name"})
    assert "plugin-name" in [f.rule for f in lint.lint_paths([tmp_path / ".claude-plugin"])]
    assert "plugin-name" in [f.rule for f in lint.lint_paths([tmp_path])]


def test_health_groups_findings_by_source(tmp_path):
    from open_skill.scan import Installed
    good = tmp_path / "good-skill"
    good.mkdir()
    (good / "SKILL.md").write_text(doc("fine"), encoding="utf-8")
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "SKILL.md").write_text(doc("fine", name="not-bad"), encoding="utf-8")
    installed = [Installed("pack/good-skill", "good-skill", str(good / "SKILL.md"), "", False),
                 Installed("pack/bad", "bad", str(bad / "SKILL.md"), "", False),
                 Installed("claude-code-builtin/code-review", "code-review", "builtin:CLAUDECODE", "", False)]
    report = lint.health(installed)
    assert report == {"pack": {"skills": 2, "errors": 1, "warnings": 0, "worst": ["bad: name-matches-folder"]}}


def test_every_rule_has_one_severity_and_a_public_source():
    for r in lint.RULES.values():
        assert r.severity in ("error", "warning") and r.source.startswith("https://") and r.checks, r.id


def test_findings_take_severity_from_the_rule_table(tmp_path):
    # name-matches-folder and missing-reference used to fall back to "error" because SEVERITY did not list them.
    d = tmp_path / "other"
    d.mkdir()
    (d / "SKILL.md").write_text(doc("[gone](references/gone.md) Double-check your work. " + "MUST x\n" * 6), encoding="utf-8")
    found = lint.lint_file(d / "SKILL.md")
    assert {f.rule for f in found} >= {"name-matches-folder", "missing-reference", "redundant-verification", "shouting"}
    for f in found:
        assert f.severity == lint.RULES[f.rule].severity, f.rule


@pytest.mark.parametrize("text,why", [
    ("no frontmatter at all\n", "start with"),
    ("---\nname: good-skill\ndescription: x\n", "closing"),
    ("---\nname: good-skill\ndescription: Dùng khi cần: kết nối dữ liệu\n---\nbody", "line 3"),  # unquoted ': '
    ("---\n- a\n- b\n---\nbody", "mapping"),
])
def test_broken_frontmatter_is_named_instead_of_reporting_missing_fields(text, why):
    found = lint.lint_text(text)
    assert [f.rule for f in found] == ["frontmatter"]
    assert why in found[0].message


def test_quoted_colon_and_crlf_frontmatter_are_fine():
    text = '---\r\nname: good-skill\r\ndescription: "Dùng khi cần: kết nối dữ liệu"\r\n---\r\nbody\r\n'
    assert rules(text) == []


@pytest.mark.parametrize("field,value", [
    ("name", "2024"),            # a YAML int; str() made it look like a valid name
    ("name", "true"),
    ("description", "[a, b]"),   # a list; str() made it a non-empty description
    ("description", "2024-01-01"),
    ("description", "'   '"),    # blank
    ("description", "~"),        # null
])
def test_name_and_description_must_be_non_empty_strings(field, value):
    values = {"name": "good-skill", "description": "Does a thing.", field: value}
    text = f"---\nname: {values['name']}\ndescription: {values['description']}\n---\nbody"
    assert f"frontmatter-{field}" in rules(text)


def test_yaml_alias_bomb_in_description_is_not_expanded():
    lines = ["a0: &a0 [x, x, x, x, x, x, x, x, x, x]"]
    lines += [f"a{i}: &a{i} [*a{i-1}, *a{i-1}, *a{i-1}, *a{i-1}, *a{i-1}, *a{i-1}, *a{i-1}, *a{i-1}, *a{i-1}, *a{i-1}]"
              for i in range(1, 9)]
    text = "---\nname: good-skill\n" + "\n".join(lines).replace("a8:", "description:") + "\n---\nbody"
    found = rules(text)  # str() of this value would build 10**9 items
    assert "frontmatter-description" in found


@pytest.mark.parametrize("desc", [">\n  Folded over\n  two lines.", "|\n  Literal\n  block.", "&d Anchored.", '"Quoted: colon."'])
def test_yaml_scalar_styles_are_valid_descriptions(desc):
    assert rules(f"---\nname: good-skill\ndescription: {desc}\n---\nbody") == []


@pytest.mark.parametrize("name,rule", [
    ("claude-helper", "name-reserved-word"),
    ("my-anthropic-tools", "name-reserved-word"),
    ("phân-tích-dữ-liệu", "name-ascii"),  # the Agent Skills reference validator accepts Unicode lowercase letters
    ("数据分析", "name-ascii"),
    ("Phân-tích", "frontmatter-name"),     # uppercase is invalid everywhere
    ("a" * 65, "frontmatter-name"),
])
def test_name_rules_each_cite_their_own_source(name, rule):
    found = {f.rule: f for f in lint.lint_text(doc("x", name=name))}
    assert rule in found and found[rule].source == lint.RULES[rule].source
    assert not ({"frontmatter-name", "name-ascii", "name-reserved-word"} - {rule}) & set(found)


def test_unicode_name_matches_a_folder_in_another_normal_form(tmp_path):
    # macOS and some zip tools store names decomposed (NFD); the frontmatter is usually composed (NFC).
    import unicodedata
    d = tmp_path / unicodedata.normalize("NFD", "phân-tích")
    d.mkdir()
    (d / "SKILL.md").write_text(doc("x", name=unicodedata.normalize("NFC", "phân-tích")), encoding="utf-8")
    assert "name-matches-folder" not in [f.rule for f in lint.lint_file(d / "SKILL.md")]


def test_description_angle_brackets_are_their_own_rule():
    found = {f.rule: f for f in lint.lint_text(doc("x", desc="Use the `<ViewTransition>` component"))}
    assert list(found) == ["description-angle-brackets"]
    assert "quick_validate" in found["description-angle-brackets"].source
    assert rules(doc("x", desc="a" * 1024)) == [] and rules(doc("x", desc="a" * 1025)) == ["frontmatter-description"]


@pytest.mark.parametrize("lines,fires", [(500, False), (501, True)])
@pytest.mark.parametrize("eol", ["\n", "\r\n"])
def test_length_counts_lines_not_newlines(lines, fires, eol):
    # A 500-line file ends with a newline, which used to count as line 501.
    head = HEAD.format(name="good-skill", desc="Does a thing.").replace("\n", eol)
    text = head + eol.join(["x"] * (lines - 4)) + eol
    assert len(text.splitlines()) == lines
    assert ("length" in rules(text)) is fires


@pytest.mark.parametrize("body,fires", [
    ("word " * 4200, True),     # about 5250 tokens of English
    ("word " * 3800, False),
    ("数据" * 3000, True),       # 6000 CJK characters are roughly 6000 tokens, not 6000 / 4
    ("数据" * 2000, False),
], ids=["english-long", "english-short", "cjk-long", "cjk-short"])
def test_body_tokens_estimate_counts_non_latin_text(body, fires):
    assert ("body-tokens" in rules(doc(body))) is fires


def test_shouting_ignores_code_blocks():
    code = "```python\n" + "logging.log(logging.CRITICAL, 'x')\n" * 6 + "```\n"
    assert "shouting" not in rules(doc(code))
    assert "shouting" not in rules(doc("~~~\n" + "IMPORTANT = 1\n" * 6 + "~~~\n"))
    assert "shouting" in rules(doc(code + "MUST a\nMUST b\nNEVER c\nALWAYS d\nCRITICAL e\nIMPORTANT f\n"))


def test_shouting_cites_the_guidance_that_says_to_dial_it_back():
    (f,) = [f for f in lint.lint_text(doc("MUST a\nMUST b\nNEVER c\nALWAYS d\nCRITICAL e\nIMPORTANT f\n"))]
    assert f.source.startswith(lint.PRACTICES)


@pytest.mark.parametrize("body,rule", [
    ('{"model": "x", "temperature": 0.7}', "sampling-params"),   # JSON quotes the key
    ("client.messages.create(top_p=0.9)", "sampling-params"),
    ("Set top_k: 40", "sampling-params"),
    ("temperature = 1", "sampling-params"),
    ('thinking: {type: "enabled", budget_tokens: 8000}', "legacy-params"),
    ("Prefill the assistant turn with an open brace.", "legacy-params"),
])
def test_removed_api_parameters(body, rule):
    assert rule in rules(doc(body))


@pytest.mark.parametrize("body", [
    "The sensor table has columns id, temperature: float, humidity: float.",
    "Report the temperature in Celsius.",
    "top_p is not accepted on current models; describe the variety you want instead.",
])
def test_sampling_params_ignore_mentions_without_a_value(body):
    assert "sampling-params" not in rules(doc(body))


@pytest.mark.parametrize("body,fires", [
    ("Use claude-opus-5-5 for planning.", True),
    ("model: claude-3-5-sonnet-20241022", True),      # dated ids put the version first
    ("anthropic.claude-3-haiku-20240307-v1:0 on Bedrock", True),
    ("Install claude-code, then read claude-api docs and CLAUDE.md.", False),
    ("Works on any Claude model.", False),
])
def test_hardcoded_model_ids(body, fires):
    assert ("hardcoded-model" in rules(doc(body))) is fires


def test_hardcoded_model_cites_this_standard():
    (f,) = [f for f in lint.lint_text(doc("Use claude-opus-5.")) if f.rule == "hardcoded-model"]
    assert "open-skill-standard" in f.source and "SPEC.md" in f.source


@pytest.mark.parametrize("body", ["Don’t nitpick style.", "Do not nitpick.", "Only report high severity bugs.", "Be conservative."])
def test_review_filtering_phrasings(body):
    assert "review-filtering" in rules(doc(body, name="code-review-pass", desc="Reviews a diff."))


def test_review_filtering_needs_a_review_skill_not_a_preview_one():
    assert "review-filtering" not in rules(doc("Be conservative with memory.", name="image-preview", desc="Preview images."))


@pytest.mark.parametrize("body,expected", [
    ("[guide](references/guide.md)", []),
    ("[gone](references/gone.md)", ["missing-reference"]),
    ("[gone](./references/gone.md#part)", ["missing-reference"]),
    ("Do not write `[text](url)` in Slack.", []),                    # a link inside inline code is an example
    ("Write links as `[text](references/x.md)`.", []),
    ("```markdown\nSee [the reference](references/REFERENCE.md).\n```", []),
    ("~~~\n[x](references/gone.md)\n~~~", []),
    ("> Also helpful: [Title](URL) and [name](link).", []),          # template placeholders, not files
    ("[my notes](references/my%20notes.md)", []),                     # URL-encoded space
    ("[my notes](<references/my notes.md>)", []),                     # CommonMark angle-bracket destination
    ("[missing](<references/no such.md>)", ["missing-reference"]),
    ('[guide](references/guide.md "The guide")', []),
    ("Write `references/[domain].md` for each domain.", []),         # a placeholder the skill fills in
    ("Check `references/examples/` first.", ["missing-mention"]),     # named in code, not linked: a warning
    ("[mail](mailto:a@example.org) [top](#top) [web](https://x.org/a.md) [abs](/etc/x.md)", []),
    ("[日本語](references/ガイド.md)", []),
    ("[tiếng việt](references/hướng-dẫn.md)", []),
])
def test_missing_reference_cases(tmp_path, body, expected):
    d = tmp_path / "good-skill"
    (d / "references").mkdir(parents=True)
    for name in ("guide.md", "my notes.md", "ガイド.md", "hướng-dẫn.md"):
        (d / "references" / name).write_text("ok", encoding="utf-8")
    (d / "SKILL.md").write_text(doc(body), encoding="utf-8")
    found = lint.lint_file(d / "SKILL.md")
    assert [f.rule for f in found] == expected
    assert all(f.severity == lint.RULES[f.rule].severity for f in found)


# Every field in the Claude Code frontmatter reference (code.claude.com/docs/en/skills#frontmatter-reference).
CLAUDE_CODE_FIELDS = ["when_to_use", "argument-hint", "arguments", "disable-model-invocation", "user-invocable",
                      "disallowed-tools", "model", "effort", "context", "agent", "background", "hooks", "paths", "shell"]


@pytest.mark.parametrize("key", CLAUDE_CODE_FIELDS)
def test_documented_claude_code_fields_are_known(key):
    assert "unknown-field" not in rules(fm(f"{key}: x"))


@pytest.mark.parametrize("key", ["version", "homepage", "triggers", "descripton"])
def test_undocumented_fields_warn(key):
    # The spec's own example keeps version under metadata; no agent reads a top-level one.
    assert rules(fm(f"{key}: x")) == ["unknown-field"]


def test_every_finding_cites_its_rule_source():
    text = fm("version: 1\nlicense: {a: b}\nallowed-tools: [Read]", "Only report high-severity bugs. " + "MUST\n" * 6 + "\n" * 500)
    found = lint.lint_text(text.replace("good-skill", "review-bot"), folder="other")
    assert len({f.rule for f in found}) >= 6
    for f in found:
        assert f.source == lint.RULES[f.rule].source, f.rule


@pytest.mark.parametrize("manifest,expected", [
    ({"name": "tools", "version": "1.2.3", "description": "d"}, []),
    ({"name": "tools", "version": "2026.09", "description": "d"}, ["plugin-version"]),  # accepted, not semver
    ({"name": "My_Tools", "description": "d"}, ["plugin-name-style"]),                   # loads, but not kebab-case
    ({"name": "my tools", "description": "d"}, ["plugin-name"]),
    ({"name": "a@b", "description": "d"}, ["plugin-name"]),
    ({"name": "a/b", "description": "d"}, ["plugin-name"]),
    ({"name": "a‮b", "description": "d"}, ["plugin-name"]),                          # bidi override
    ({"description": "d"}, ["plugin-name"]),
    ({"name": 7, "description": "d"}, ["plugin-name"]),
    ({"name": "công-cụ", "description": "d"}, ["plugin-name-style"]),
    ([1, 2], ["manifest-json"]),
])
def test_plugin_manifest_cases(tmp_path, manifest, expected):
    found = lint.lint_plugin(write_json(tmp_path, "plugin.json", manifest))
    assert [f.rule for f in found] == expected
    assert all(f.source == lint.RULES[f.rule].source for f in found)
    assert all(f.source.startswith(lint.PLUGIN_DOCS) for f in found if f.rule.startswith("plugin-"))


def mkt(**kw):
    base = {"name": "tools", "description": "d", "owner": {"name": "me"},
            "plugins": [{"name": "a", "source": "./plugins/a"}]}
    base.update(kw)
    return base


@pytest.mark.parametrize("manifest,expected", [
    (mkt(), []),
    (mkt(plugins=[{"name": "a", "source": "."}]), []),
    (mkt(plugins=[{"name": "a", "source": {"source": "github", "repo": "o/r"}}]), []),
    (mkt(plugins=[{"name": "a", "source": "plugins/a"}]), ["marketplace-source"]),      # relative paths start with ./
    (mkt(plugins=[{"name": "a", "source": "a"}], metadata={"pluginRoot": "./plugins"}), []),
    (mkt(plugins=[{"name": "a", "source": "./x/../../y"}]), ["marketplace-source"]),
    (mkt(plugins={"a": {"source": "./a"}}), ["marketplace-field"]),                     # an object, not a list: crashed
    (mkt(plugins=["a"]), ["marketplace-plugin"]),                                        # entry not an object: crashed
    (mkt(plugins=[{"name": "a", "source": "./a"}, {"name": "a", "source": "./b"}]), ["marketplace-plugin"]),
    (mkt(plugins=[{"name": "my plugin", "source": "./a"}]), ["marketplace-plugin"]),
    (mkt(owner={"email": "x@example.org"}), ["marketplace-field"]),
    (mkt(owner="me"), ["marketplace-field"]),
    (mkt(name="my tools"), ["marketplace-name"]),
    (mkt(name="../up"), ["marketplace-name"]),
    (mkt(name=""), ["marketplace-name"]),
    (mkt(name="claude-plugins-official"), ["marketplace-reserved"]),
    (mkt(name="claude.code.plugins"), ["marketplace-reserved"]),                         # another spelling of a reserved name
    (mkt(name="NPM"), ["marketplace-reserved"]),
    (mkt(name="claudeai-team"), ["marketplace-reserved"]),
    (mkt(name="acme-official-tools"), ["marketplace-reserved"]),
    (mkt(name="công-cụ"), ["marketplace-name"]),                                         # non-ASCII impersonates
    (mkt(name="my+tools"), ["marketplace-name"]),                                        # only letters, digits, . _ -
    (mkt(name="-tools"), ["marketplace-name"]),                                          # starts with a letter or digit
    (mkt(name="tools_v2.1"), []),
    (mkt(plugins=[{"name": "a+b", "source": "./a"}]), ["marketplace-plugin"]),
    (mkt(plugins=[{"name": "ünï", "source": "./a"}]), ["marketplace-plugin"]),
    (mkt(plugins=[{"name": ".hidden", "source": "./a"}]), ["marketplace-plugin"]),
    ([], ["manifest-json"]),
])
def test_marketplace_manifest_cases(tmp_path, manifest, expected):
    found = lint.lint_marketplace(write_json(tmp_path, "marketplace.json", manifest))
    assert [f.rule for f in found] == expected
    assert all(f.source == lint.RULES[f.rule].source for f in found)


@pytest.mark.parametrize("body,fires", [
    ("Show your reasoning in the response.", True),
    ("Include your chain-of-thought in the answer.", True),
    ("Think step by step and write it out for the user.", True),
    ("Do not include your reasoning in the response.", False),   # the advice the rule asks for
    ("Don’t show your thinking in the reply; give the result.", False),
    ("Explain the trade-offs in the response.", False),
])
def test_reasoning_in_response(body, fires):
    assert ("reasoning-in-response" in rules(doc(body))) is fires


@pytest.mark.parametrize("body,fires", [
    ("Double-check your answer before replying.", True),
    ("Re-verify before responding.", True),
    ("Verify your work again at the end.", True),
    ("Run the tests to verify the change.", False),
    ("Check the answer against the spec.", False),
])
def test_redundant_verification(body, fires):
    assert ("redundant-verification" in rules(doc(body))) is fires
