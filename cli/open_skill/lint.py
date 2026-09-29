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
    out = []
    for p in map(Path, paths):
        files = sorted(p.rglob("SKILL.md")) if p.is_dir() else [p]
        for f in files:
            out += lint_file(f)
    return out
