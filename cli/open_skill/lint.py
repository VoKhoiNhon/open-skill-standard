"""Lint SKILL.md files: frontmatter limits and prompt patterns that current Claude models handle badly."""

import re
from dataclasses import dataclass
from pathlib import Path

from . import frontmatter

BEST = "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices"
FABLE5 = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5"
OPUS5 = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5"
SONNET5 = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5"
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
NAME_RX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


# Errors break skills on some agent or model; warnings are strong advice.
SEVERITY = {
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


def lint_text(text: str, path: str = "<text>") -> list[Finding]:
    out: list[Finding] = []
    meta, body = frontmatter.parse(text)

    def add(rule, msg, src):
        out.append(Finding(path, rule, msg, src, SEVERITY.get(rule, "error")))

    name, desc = str(meta.get("name", "")), str(meta.get("description", ""))
    if not name:
        add("frontmatter-name", "name is missing", BEST)
    elif len(name) > 64 or not NAME_RX.match(name) or "claude" in name or "anthropic" in name:
        add("frontmatter-name", "name must be kebab-case, at most 64 chars, without 'claude' or 'anthropic'", BEST)
    if not desc:
        add("frontmatter-description", "description is missing", BEST)
    elif len(desc) > 1024 or "<" in desc or ">" in desc:
        add("frontmatter-description", "description must be at most 1024 chars with no angle brackets", BEST)
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


def lint_file(path: Path) -> list[Finding]:
    return lint_text(Path(path).read_text(errors="replace"), str(path))


def lint_paths(paths) -> list[Finding]:
    out = []
    for p in map(Path, paths):
        files = sorted(p.rglob("SKILL.md")) if p.is_dir() else [p]
        for f in files:
            out += lint_file(f)
    return out
