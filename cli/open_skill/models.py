"""Resolve the model profile for the model the agent is running on."""

import fnmatch
import re

LIST_KEYS = ("addenda", "avoid")
FAMILY = re.compile(r"^claude-([a-z]+)-")


def _normalize(model_id: str) -> str:
    """Lowercase, without a context suffix like [1m] or a provider prefix like us.anthropic. or anthropic/."""
    mid = re.sub(r"\[.*?\]", "", model_id.strip().lower())
    return re.sub(r"^[a-z0-9._/-]*?(?=claude-)", "", mid)


def _merge(base: dict, child: dict) -> dict:
    out = dict(base)
    for k, v in child.items():
        if k in LIST_KEYS:
            out[k] = list(dict.fromkeys([*out.get(k, []), *v]))
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out


def _chain(pid: str, profiles: dict) -> list[str]:
    chain, cur = [], pid
    while cur:
        if cur in chain:
            raise ValueError(f"inheritance cycle: {' -> '.join(chain + [cur])}")
        chain.append(cur)
        cur = profiles.get(cur, {}).get("inherits")
    if chain[-1] != "generic" and "generic" in profiles:
        chain.append("generic")
    return list(reversed(chain))


def _pick(model_id: str | None, profiles: dict) -> tuple[str, str]:
    if not model_id:
        return "generic", "default"
    mid = _normalize(model_id)
    specific = [p for p in profiles.values() if p["id"] != "generic"]
    # Longest matching glob wins, so "claude-opus-5-5*" beats "claude-opus-5*".
    hits = [(len(g), p["id"]) for p in specific for g in p.get("match", []) if fnmatch.fnmatch(mid, g.lower())]
    if hits:
        return max(hits)[1], "exact"
    m = FAMILY.match(mid)
    fam = [p["id"] for p in specific if m and p.get("family") == m.group(1)]
    if fam:
        return max(fam), "family"  # newest profile id of the same family
    return "generic", "default"


def resolve(model_id: str | None, profiles: dict) -> dict:
    pid, how = _pick(model_id, profiles)
    lineage = _chain(pid, profiles)
    merged: dict = {}
    for p in lineage:
        merged = _merge(merged, {k: v for k, v in profiles[p].items() if k not in ("match", "inherits")})
    merged.update({"id": pid, "lineage": lineage, "matched_by": how, "requested": model_id})
    return merged
