import json
import re
from html.parser import HTMLParser
from pathlib import Path

from open_skill import graph_html, index, registry
from open_skill.scan import Installed

FIX = Path(__file__).parent / "fixtures"
VOID = {"meta", "link", "br", "hr", "img", "input", "col", "wbr", "source", "area", "base", "embed", "track"}


class Checker(HTMLParser):
    """Fails on unbalanced tags; collects attributes and the embedded graph data."""

    def __init__(self):
        super().__init__()
        self.stack, self.attrs, self.data, self._in_data = [], [], None, False

    def handle_starttag(self, tag, attrs):
        self.attrs.append((tag, dict(attrs)))
        if tag not in VOID:
            self.stack.append(tag)
        self._in_data = tag == "script" and dict(attrs).get("id") == "graph-data"

    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1] == tag, f"unexpected </{tag}> after {self.stack[-3:]}"
        self.stack.pop()
        self._in_data = False

    def handle_data(self, data):
        if self._in_data:
            self.data = json.loads(data)


def page(description="Write a detailed implementation plan from a spec"):
    reg = registry.load(FIX / "repo")
    reg.skills["superpowers/writing-plans"]["description"] = description
    inst = [Installed("harvested/warehouse-audit", "warehouse-audit", "/x", "Audit warehouse tables", True)]
    return graph_html.graph_html(index.graph_json(reg, inst))


def parse(html):
    c = Checker()
    c.feed(html)
    c.close()
    assert c.stack == [], f"unclosed tags: {c.stack}"
    return c


def test_page_is_valid_html_with_the_graph_data():
    html = page()
    assert html.startswith("<!doctype html>")
    c = parse(html)
    ids = {n["id"] for n in c.data["nodes"]}
    assert {"superpowers/writing-plans", "harvested/warehouse-audit", "role:data-engineer", "phase:build", "artifact:plan"} <= ids


def test_page_loads_nothing_from_the_network():
    html = page()
    c = parse(html)
    assert not re.search(r"https?://|//cdn|@import|url\(", html)
    for tag, attrs in c.attrs:
        assert "src" not in attrs, tag
        assert tag != "link"


def test_data_cannot_close_the_script_tag():
    html = page('plan </script><script>alert(1)</script>')
    c = parse(html)
    assert html.count("</script>") == 2  # the data block and the app script, nothing from the data
    desc = next(n["description"] for n in c.data["nodes"] if n["id"] == "superpowers/writing-plans")
    assert desc == "plan </script><script>alert(1)</script>"
