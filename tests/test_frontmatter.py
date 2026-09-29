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
