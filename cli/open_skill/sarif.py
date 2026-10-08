"""SARIF 2.1.0 logs for audit and lint findings, so code scanning (GitHub, IDE SARIF viewers) can show them.

One run per log; the rule catalog is listed in full so a viewer can explain any rule id. Paths inside the base
folder (normally the current folder, the repository root in CI) are written relative to it, others as file URIs.
"""

import hashlib
import os
from pathlib import Path
from urllib.parse import quote

from . import __version__

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
INFO_URI = "https://github.com/VoKhoiNhon/open-skill-standard"
LEVEL = {"high": "error", "medium": "warning", "low": "note", "error": "error", "warning": "warning"}
# GitHub code scanning ranks security alerts by this property: 7.0+ is high, 4.0–6.9 medium, below 4.0 low.
SECURITY_SEVERITY = {"high": "8.0", "medium": "5.0", "low": "2.0"}
FINGERPRINT = "openSkillFinding/v1"


def _fingerprint(rule: str, uri: str, text: str, seen: dict) -> str:
    """Stable across runs while the finding stays: rule, file and the flagged text with its whitespace collapsed,
    not the line, so an edit above it keeps the alert. The nth repeat of the same text in a file is told apart
    (so adding a copy above a finding renumbers it). Paths are relative to the base, so run from one folder."""
    key = (rule, uri, " ".join(text.split()))
    seen[key] = seen.get(key, 0) + 1
    return hashlib.sha256("\0".join([*key, str(seen[key])]).encode("utf-8")).hexdigest()


def _location(path: str, line: int, snippet: str, base: Path) -> dict:
    # Relative paths are relative to the current folder, not to base, and may hold "..": normalize them first.
    p = Path(os.path.abspath(path))
    artifact = {"uri": p.as_uri()}
    for candidate in (p, p.resolve()):  # resolved too, as base is, so a linked or short-named folder still matches
        try:
            artifact = {"uri": quote(candidate.relative_to(base).as_posix()), "uriBaseId": "SRCROOT"}
            break
        except ValueError:
            pass
    physical = {"artifactLocation": artifact}
    if line >= 1:  # SARIF lines start at 1; file-level findings (links, binaries) carry no region
        physical["region"] = {"startLine": line, **({"snippet": {"text": snippet}} if snippet else {})}
    return {"physicalLocation": physical}


def log(rules: list[dict], results: list[dict], base: Path | None = None) -> dict:
    """A SARIF log from rule dicts (id, severity, text, source, security) and result dicts
    (rule, severity, message, path, line, snippet, and optional properties)."""
    base = Path(base or Path.cwd()).resolve()
    index = {r["id"]: i for i, r in enumerate(rules)}
    driver_rules = []
    for r in rules:
        props = {"tags": ["security"] if r.get("security") else ["maintainability"]}
        if r.get("security"):
            props["security-severity"] = SECURITY_SEVERITY[r["severity"]]
        driver_rules.append({"id": r["id"], "shortDescription": {"text": r["text"]}, "helpUri": r["source"],
                             "defaultConfiguration": {"level": LEVEL[r["severity"]]}, "properties": props})
    out, seen = [], {}
    for f in results:
        loc = _location(f["path"], f.get("line", 0), f.get("snippet", ""), base)
        uri = loc["physicalLocation"]["artifactLocation"]["uri"]
        res = {"ruleId": f["rule"], "level": LEVEL[f["severity"]], "message": {"text": f["message"]},
               "locations": [loc],
               "partialFingerprints": {FINGERPRINT: _fingerprint(f["rule"], uri, f.get("snippet") or f["message"], seen)}}
        if f["rule"] in index:
            res["ruleIndex"] = index[f["rule"]]
        if f.get("properties"):
            res["properties"] = f["properties"]
        out.append(res)
    return {"$schema": SCHEMA, "version": "2.1.0", "runs": [{
        "tool": {"driver": {"name": "open-skill", "version": __version__, "semanticVersion": __version__,
                            "informationUri": INFO_URI, "rules": driver_rules}},
        "originalUriBaseIds": {"SRCROOT": {"uri": base.as_uri().rstrip("/") + "/"}},
        "results": out}]}
