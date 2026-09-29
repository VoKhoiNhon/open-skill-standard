"""Lint SKILL.md files: frontmatter limits and prompt patterns that current Claude models handle badly."""

import re
from dataclasses import dataclass
from pathlib import Path

from . import frontmatter

BEST = "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices"
FABLE5 = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5"
OPUS5 = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5"
SONNET5 = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5"
SPEC = "https://agentskills.io/specification"
PRACTICES = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices"

PATTERNS = [
    ("reasoning-in-response",
     re.compile(r"(?i)(show|write out|reproduce|explain|include|output) (all |your |the )?(reasoning|thinking|chain[- ]of[- ]thought)"
                r"( process)?( in| into)? (the |your )?(response|answer|reply|output)|think step[- ]by[- ]step (in|and write)"),
     "Asking the model to reproduce its reasoning in the reply can be declined as reasoning_extraction.", FABLE5),
    ("redundant-verification",
     re.compile(r"(?i)\b(double[- ]check your|re-?verify (your|before)|verify (it|your work) again)"),
     "Current models self-verify; extra verification instructions cause over-verification.", OPUS5),
    ("hardcoded-model",
     re.compile(r"(?i)\bclaude-(opus|sonnet|haiku|fable|mythos)-\d"),
     "Model IDs belong in registry/models profiles, not in skills.", PRACTICES),
    ("legacy-params",
     re.compile(r"(?i)\b(budget_tokens|temperature\s*[=:]|prefill(ed)? (the )?(assistant|response))"),
     "budget_tokens, temperature and prefills are removed or rejected on current models.", PRACTICES),
]
REVIEW_FILTER = re.compile(r"(?i)(only report (high|critical)[- ]severity|be conservative|don'?t nitpick)")
SHOUT = re.compile(r"\b(MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT)\b")
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
# Extensions some agents read (Claude Code documents these); everything else is probably a typo.
AGENT_FIELDS = {"when_to_use", "argument-hint", "disable-model-invocation", "user-invocable", "model", "effort",
                "context", "agent", "hooks", "paths", "version"}
CLAUDE_SKILLS = "https://code.claude.com/docs/en/skills"
NAME_RX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")  # no leading, trailing or double hyphens (Agent Skills spec)


# Errors break skills on some agent or model; warnings are strong advice.
SEVERITY = {
    "field-allowed-tools": "warning", "field-license": "warning", "unknown-field": "warning", "body-tokens": "warning",
    "frontmatter-name": "error", "frontmatter-description": "error", "reasoning-in-response": "error",
    "legacy-params": "error", "length": "warning", "redundant-verification": "warning",
    "hardcoded-model": "warning", "review-filtering": "warning", "shouting": "warning",
}


@dataclass
class Finding:
    path: str
    rule: str
    message: str
    source: str
    severity: str = "error"


def lint_text(text: str, path: str = "<text>", folder: str | None = None) -> list[Finding]:
    out: list[Finding] = []
    meta, body = frontmatter.parse(text)

    def add(rule, msg, src):
        out.append(Finding(path, rule, msg, src, SEVERITY.get(rule, "error")))

    name, desc = str(meta.get("name", "")), str(meta.get("description", ""))
    if not name:
        add("frontmatter-name", "name is missing", BEST)
    elif len(name) > 64 or not NAME_RX.match(name):
        add("frontmatter-name", "name must be 1-64 lowercase letters, digits and single hyphens, not starting or ending with a hyphen", SPEC)
    elif "claude" in name or "anthropic" in name:
        add("frontmatter-name", "name must not contain 'claude' or 'anthropic'", BEST)
    if name and folder and name != folder:
        add("name-matches-folder", f"name '{name}' must match its folder '{folder}'", SPEC)
    if not desc:
        add("frontmatter-description", "description is missing", BEST)
    elif len(desc) > 1024 or "<" in desc or ">" in desc:
        add("frontmatter-description", "description must be at most 1024 chars with no angle brackets", BEST)
    for key in sorted(set(meta) - SPEC_FIELDS - AGENT_FIELDS):
        add("unknown-field", f"'{key}' is not an Agent Skills field; agents will ignore it (put custom data under metadata)", SPEC)
    if "compatibility" in meta and not (isinstance(meta["compatibility"], str) and 1 <= len(meta["compatibility"]) <= 500):
        add("field-compatibility", "compatibility must be a string of 1-500 characters", SPEC)
    md = meta.get("metadata")
    if "metadata" in meta and not (isinstance(md, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in md.items())):
        add("field-metadata", "metadata must map string keys to string values (quote numbers like \"1.0\")", SPEC)
    if "allowed-tools" in meta and not isinstance(meta["allowed-tools"], str):
        add("field-allowed-tools", "allowed-tools should be one space-separated string", SPEC)
    if "license" in meta and not isinstance(meta["license"], str):
        add("field-license", "license should be a short string or the name of a bundled license file", SPEC)
    if len(body) / 4 > 5000:  # rough token estimate; the spec recommends under 5000 tokens for instructions
        add("body-tokens", f"instructions are about {len(body) // 4} tokens; keep SKILL.md under ~5000 and move detail to references/", SPEC)
    if text.count("\n") + 1 > 500:
        add("length", "SKILL.md over 500 lines; move detail into reference files", BEST)
    for rule, rx, msg, src in PATTERNS:
        if rx.search(body):
            add(rule, msg, src)
    if re.search(r"(?i)review", name + " " + desc) and REVIEW_FILTER.search(body):
        add("review-filtering", "Review instructions that filter by severity cut recall on current models; report all and filter later.", SONNET5)
    if sum(1 for line in body.splitlines() if SHOUT.search(line)) > 5:
        add("shouting", "Explain why instead of capitalized MUST/NEVER; current models follow brief instructions.", FABLE5)
    return out


LINK = re.compile(r"\]\(([^)\s]+)\)|`((?:references|scripts|assets)/[^`\s]+)`")


def missing_references(body: str, base: Path) -> list[str]:
    """Relative files a skill points to that do not exist (URLs, anchors and <placeholders> are skipped)."""
    out = []
    for m in LINK.finditer(body):
        ref = (m.group(1) or m.group(2)).split("#")[0]
        if not ref or re.match(r"^[a-z]+:", ref) or ref.startswith(("/", "~")) or re.search(r"[<>{}*]", ref):
            continue
        if not (base / ref).exists():
            out.append(ref)
    return sorted(set(out))


def lint_file(path: Path) -> list[Finding]:
    path = Path(path)
    folder = path.parent.name if path.name == "SKILL.md" else None
    text = path.read_text(errors="replace")
    out = lint_text(text, str(path), folder)
    for ref in missing_references(frontmatter.parse(text)[1], path.parent):
        out.append(Finding(str(path), "missing-reference", f"references '{ref}', which does not exist", SPEC))
    return out


def lint_paths(paths) -> list[Finding]:
    """Lint SKILL.md files and any Claude plugin manifests found under the given paths."""
    out = []
    for p in map(Path, paths):
        files = sorted(p.rglob("SKILL.md")) if p.is_dir() else [p]
        manifests = sorted(p.rglob(".claude-plugin/*.json")) if p.is_dir() else []
        if p.is_dir() and p.name == ".claude-plugin":
            manifests = sorted(p.glob("*.json"))
        for f in files:
            if f.name == "marketplace.json":
                out += lint_marketplace(f)
            elif f.name == "plugin.json":
                out += lint_plugin(f)
            else:
                out += lint_file(f)
        for m in manifests:
            out += lint_marketplace(m) if m.name == "marketplace.json" else lint_plugin(m) if m.name == "plugin.json" else []
    return out


MARKETPLACE_DOCS = "https://code.claude.com/docs/en/plugin-marketplaces"


def lint_marketplace(path: Path) -> list[Finding]:
    """Required fields of .claude-plugin/marketplace.json, as the Claude Code validator checks them."""
    import json

    path = Path(path)
    out: list[Finding] = []

    def add(rule, msg, sev="error"):
        out.append(Finding(str(path), rule, msg, MARKETPLACE_DOCS, sev))

    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        add("manifest-json", f"invalid JSON: {e}")
        return out
    for key in ("name", "owner", "plugins"):
        if key not in doc:
            add("marketplace-field", f"missing required field '{key}'")
    for i, p in enumerate(doc.get("plugins") or []):
        for key in ("name", "source"):
            if key not in p:
                add("marketplace-plugin", f"plugins[{i}] is missing '{key}'")
        src = p.get("source")
        if isinstance(src, str) and ".." in Path(src).parts:
            add("marketplace-source", f"plugins[{i}].source '{src}' must not leave the marketplace with '..'")
    name = str(doc.get("name", "")).lower()
    if any(w in name for w in ("anthropic", "claude-plugins-official", "official")):
        add("marketplace-name", f"marketplace name '{doc.get('name')}' looks like an official Anthropic marketplace", "warning")
    return out


SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def lint_plugin(path: Path) -> list[Finding]:
    """.claude-plugin/plugin.json: a kebab-case name, and a semantic version when one is given."""
    import json

    path = Path(path)
    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [Finding(str(path), "manifest-json", f"invalid JSON: {e}", MARKETPLACE_DOCS)]
    out = []
    if not NAME_RX.match(str(doc.get("name", ""))):
        out.append(Finding(str(path), "plugin-name", "plugin name must be kebab-case", MARKETPLACE_DOCS))
    if "version" in doc and not SEMVER.match(str(doc["version"])):
        out.append(Finding(str(path), "plugin-version", f"version '{doc['version']}' is not semantic (x.y.z)", MARKETPLACE_DOCS))
    if not doc.get("description"):
        out.append(Finding(str(path), "plugin-description", "add a description so people know what the plugin does",
                           MARKETPLACE_DOCS, "warning"))
    return out
