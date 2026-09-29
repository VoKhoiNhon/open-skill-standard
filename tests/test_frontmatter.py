from open_skill import frontmatter


def test_parses_frontmatter_and_body():
    assert frontmatter.parse("---\nname: a\ndescription: b\n---\nbody") == ({"name": "a", "description": "b"}, "body")


def test_no_frontmatter_returns_text():
    assert frontmatter.parse("just text") == ({}, "just text")


def test_malformed_yaml_never_raises():
    text = "---\nname: [unclosed\n---\nbody"
    assert frontmatter.parse(text) == ({}, text)


def test_crlf():
    assert frontmatter.parse("---\r\nname: a\r\n---\r\nbody")[0] == {"name": "a"}


def test_non_mapping_frontmatter():
    text = "---\n- a\n- b\n---\nbody"
    assert frontmatter.parse(text) == ({}, text)


def test_byte_order_mark_is_ignored():
    # Editors on Windows save UTF-8 with a BOM; the frontmatter was lost and lint said "name is missing".
    assert frontmatter.parse("﻿---\nname: a\n---\nbody") == ({"name": "a"}, "body")


def test_empty_frontmatter_does_not_swallow_the_body():
    # The closing --- right after the opening one was missed, so a later --- rule in the body closed it.
    assert frontmatter.parse("---\n---\nbody\n\n---\nmore") == ({}, "body\n\n---\nmore")



def test_text_returns_only_string_values():
    meta = {"name": "a", "n": 7, "l": ["x"], "none": None}
    assert [frontmatter.text(meta, k) for k in ("name", "n", "l", "none", "absent")] == ["a", "", "", "", ""]
    assert frontmatter.text(meta, "n", "fallback") == "fallback"
