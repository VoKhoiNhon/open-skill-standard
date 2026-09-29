"""Starter knowledge (role pack seeds): no two roles ship the same advice."""

import itertools
import re

from open_skill import registry

SHIPPED = {f"{rid}/{s['id']}": s["text"] for rid, r in registry.load().roles.items() for s in r.get("seeds", [])}
STOP = {"a", "an", "and", "or", "the", "of", "to", "in", "on", "for", "with", "is", "are", "be", "it", "its",
        "before", "after", "every", "each", "not", "no"}


def _words(text: str) -> set[str]:
    return {w.removesuffix("s") for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP}


def test_no_two_roles_ship_the_same_advice():
    # A user with both roles would get the same note twice.
    pairs = [(a, b) for (a, ta), (b, tb) in itertools.combinations(SHIPPED.items(), 2)
             if a.split("/")[0] != b.split("/")[0]
             and len(_words(ta) & _words(tb)) / len(_words(ta) | _words(tb)) >= 0.4]
    assert not pairs, pairs
