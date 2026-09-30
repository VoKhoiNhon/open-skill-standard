"""Lint SKILL.md files: frontmatter limits and prompt patterns that current Claude models handle badly."""

import re
import unicodedata
from urllib.parse import unquote
from dataclasses import dataclass
from pathlib import Path

from . import frontmatter

BEST = "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices"
FABLE5 = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5"
OPUS5 = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5"
SONNET5 = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5"
SPEC = "https://agentskills.io/specification"
SKILLS_REF = "https://github.com/agentskills/agentskills/blob/main/skills-ref/src/skills_ref/validator.py"
QUICK_VALIDATE = "https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/quick_validate.py"
OSS_SPEC = "https://github.com/VoKhoiNhon/open-skill-standard/blob/main/spec/SPEC.md#7-skill-writing-rules"
PRACTICES = "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices"

PATTERNS = [
    ("reasoning-in-response", "error",
     re.compile(r"(?i)(?<!not )(?<!n't )(?<!n’t )(?<!never )"
                r"(show|write out|reproduce|explain|include|output) (all |your |the )?(reasoning|thinking|chain[- ]of[- ]thought)"
                r"( process)?( in| into)? (the |your )?(response|answer|reply|output)|think step[- ]by[- ]step (in|and write)"),
     "Asking the model to reproduce its reasoning in the reply can be declined as reasoning_extraction.", FABLE5),
    ("redundant-verification", "warning",
     re.compile(r"(?i)\b(double[- ]check your|re-?verify (your|before)|verify (it|your work) again)"),
     "Current models self-verify; extra verification instructions cause over-verification.", OPUS5),
    ("hardcoded-model", "warning",
     re.compile(r"(?i)\bclaude-((opus|sonnet|haiku|fable|mythos)-\d|\d(-\d+)?-(opus|sonnet|haiku)\b)"),
     "Model IDs belong in registry/models profiles, not in skills, so a skill keeps working on the next model.", OSS_SPEC),
    ("legacy-params", "error",
     re.compile(r"(?i)\b(budget_tokens|prefill(ed)? (the )?(assistant|response))"),
     "Manual thinking budgets (budget_tokens) and assistant prefills return a 400 error on current models.", PRACTICES),
    ("sampling-params", "error",
     re.compile(r"(?i)\b(temperature|top_p|top_k)[\"']?\s*[=:]\s*[\"']?\d"),
     "Setting temperature, top_p or top_k returns a 400 error on Claude Sonnet 5; describe the variety you want instead.",
     SONNET5 + "#tone-and-writing-style"),
]
REVIEW_FILTER = re.compile(r"(?i)(only report (high|critical)[- ]severity|be conservative|(don['’]?t|do not) nitpick)")
SHOUT = re.compile(r"\b(MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT)\b")
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
# Extensions Claude Code documents in its frontmatter reference; everything else is probably a typo.
AGENT_FIELDS = {"when_to_use", "argument-hint", "arguments", "disable-model-invocation", "user-invocable",
                "disallowed-tools", "model", "effort", "context", "agent", "background", "hooks", "paths", "shell"}
CLAUDE_SKILLS = "https://code.claude.com/docs/en/skills"
# Claude Code frontmatter values (skills reference, "Frontmatter reference"); YAML reads true/false as booleans.
CLAUDE_CODE_VALUES = {"effort": ("low", "medium", "high", "xhigh", "max"), "context": ("fork",),
                      "shell": ("bash", "powershell"), "disable-model-invocation": (True, False),
                      "user-invocable": (True, False), "background": (True, False)}
LISTING_MAX = 1536
FENCE = re.compile(r"(?ms)^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*$")


def prose(body: str) -> str:
    """The body with fenced code blocks blanked out, keeping line numbers."""
    return FENCE.sub(lambda m: "\n" * m.group().count("\n"), body)


NAME_RX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")  # no leading, trailing or double hyphens (Agent Skills spec)


# Errors break skills on some agent or model; warnings are strong advice.
@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    checks: str  # what the rule looks for, as the rule catalog shows it
    source: str  # the public guidance the rule comes from


RULES: dict[str, Rule] = {}


def rule(id: str, severity: str, checks: str, source: str) -> None:
    assert severity in ("error", "warning") and id not in RULES, id
    RULES[id] = Rule(id, severity, checks, source)


MARKETPLACE_DOCS = "https://code.claude.com/docs/en/plugin-marketplaces"
PLUGIN_DOCS = "https://code.claude.com/docs/en/plugins-reference"
MARKETPLACE_REF = "https://code.claude.com/docs/en/plugins/marketplace-reference"
rule("frontmatter", "error", "SKILL.md starts with a closed block of YAML frontmatter that is a mapping", SPEC)
rule("frontmatter-name", "error", "`name` is a string of 1-64 lowercase letters, digits and single hyphens, not starting or"
     " ending with a hyphen; letters outside a-z are allowed as the reference validator allows them", SPEC)
rule("name-ascii", "warning", "`name` uses only a-z, 0-9 and hyphens, which Anthropic's packager and claude.ai uploads require",
     QUICK_VALIDATE)
rule("name-reserved-word", "error", "`name` does not contain the reserved words 'claude' or 'anthropic'", BEST)
rule("name-matches-folder", "error", "`name` equals the name of the folder holding SKILL.md, compared in Unicode NFKC form",
     SKILLS_REF)
rule("frontmatter-description", "error", "`description` is a non-blank string of at most 1024 characters", SPEC)
rule("description-angle-brackets", "error", "`description` has no `<` or `>`, which Anthropic's packager rejects", QUICK_VALIDATE)
rule("unknown-field", "warning", "every frontmatter key is an Agent Skills field or one Claude Code documents",
     CLAUDE_SKILLS + "#frontmatter-reference")
rule("field-compatibility", "error", "`compatibility`, when present, is a string of 1-500 characters", SPEC)
rule("field-metadata", "error", "`metadata`, when present, maps string keys to string values", SPEC)
rule("field-allowed-tools", "warning", "`allowed-tools`, when present, is one space-separated string", SPEC)
rule("field-claude-code", "warning", "Claude Code fields hold values it accepts: `effort` low, medium, high, xhigh or max; "
     "`context` fork; `shell` bash or powershell; true or false for `disable-model-invocation`, `user-invocable` and "
     "`background`", CLAUDE_SKILLS + "#frontmatter-reference")
rule("listing-length", "warning", "`description` and `when_to_use` together fit in the 1,536 characters Claude Code lists",
     CLAUDE_SKILLS + "#frontmatter-reference")
rule("folder-reserved", "warning", "the skill folder is not named `synced` (any case) or `anthropic-skills`, which Claude "
     "Code keeps for skills synced from claude.ai and skips", CLAUDE_SKILLS + "#where-skills-live")
rule("field-license", "warning", "`license`, when present, is a string", SPEC)
rule("body-tokens", "warning", "the SKILL.md body is under about 5000 tokens", SPEC)
rule("length", "warning", "SKILL.md is under 500 lines", BEST)
for _id, _sev, _rx, _msg, _src in PATTERNS:
    rule(_id, _sev, _msg, _src)
rule("review-filtering", "warning", "a review skill does not tell the model to report only severe findings", SONNET5)
rule("shouting", "warning", "no more than five lines outside code blocks use capitalized MUST, NEVER, ALWAYS, CRITICAL or IMPORTANT",
     PRACTICES + "#tool-usage")
rule("missing-reference", "error", "every relative file the body links to outside code exists", SPEC + "#file-references")
rule("missing-mention", "warning", "every references/, scripts/ or assets/ path the body names in inline code exists",
     SPEC + "#file-references")
rule("manifest-json", "error", "a plugin or marketplace manifest is valid JSON", MARKETPLACE_DOCS)
rule("marketplace-field", "error", "marketplace.json has `name`, `owner` (with a `name`) and a list of `plugins`",
     MARKETPLACE_REF + "#validation-messages")
rule("marketplace-plugin", "error", "every plugin entry is an object with a unique `name` of ASCII letters, digits, '.', "
     "'_' and '-' that starts with a letter or digit, and a `source`",
     MARKETPLACE_REF + "#validation-messages")
rule("marketplace-source", "error", "a relative plugin `source` starts with ./ and does not leave the marketplace with `..`; "
     "a source object has a known type and its required fields (github `repo`, url `url`, git-subdir `url` and `path`, "
     "npm `package`, archive https `url`, command `command`) in the documented form", MARKETPLACE_REF + "#plugin-sources")
rule("marketplace-name", "error", "the marketplace name uses only ASCII letters, digits, '.', '_' and '-', starts with a "
     "letter or digit and has no '..'; Claude Code cannot install plugins from any other name", MARKETPLACE_REF + "#top-level-fields")
rule("marketplace-reserved", "warning", "the marketplace name is not reserved for, and does not look like, an official "
     "Anthropic marketplace", MARKETPLACE_REF + "#reserved-names")
rule("marketplace-desktop", "warning", "marketplace and plugin names are at most 128 characters, and the marketplace is "
     "not named org, org-provisioned or unknown, which Claude Desktop rejects", MARKETPLACE_REF + "#validation-messages")
rule("marketplace-description", "warning", "marketplace.json has a `description` (or `metadata.description`)",
     MARKETPLACE_REF + "#top-level-fields")
rule("marketplace-empty", "warning", "marketplace.json lists at least one plugin", MARKETPLACE_REF + "#validation-messages")
rule("plugin-name", "error", "plugin.json `name` is a non-empty string without spaces, @, :, slashes or control characters",
     PLUGIN_DOCS + "#name")
rule("plugin-name-style", "warning", "plugin.json `name` is kebab-case, as Claude Code recommends", PLUGIN_DOCS + "#name")
rule("plugin-version", "warning", "plugin.json `version`, when present, is semantic (x.y.z); Claude Code accepts any string",
     PLUGIN_DOCS + "#version")
rule("plugin-description", "warning", "plugin.json has a `description`", PLUGIN_DOCS)


@dataclass
class Finding:
    path: str
    rule: str
    message: str
    source: str
    severity: str = "error"


def _finding(path, rule_id: str, message: str) -> Finding:
    r = RULES[rule_id]
    return Finding(str(path), rule_id, message, r.source, r.severity)


def _not_text(meta: dict, key: str) -> str | None:
    """Why a required text field is unusable, or None when it is a non-blank string."""
    v = meta.get(key)
    if v is None:
        return f"{key} is missing"
    if not isinstance(v, str):
        return f"{key} must be a string, not a YAML {type(v).__name__} (quote it)"
    return None if v.strip() else f"{key} is blank"


def _spec_name(name: str) -> bool:
    """The reference validator's test: lowercase letters (any script), digits and single inner hyphens, 1-64 long."""
    return (0 < len(name) <= 64 and name == name.lower() and not name.startswith("-") and not name.endswith("-")
            and "--" not in name and all(c.isalnum() or c == "-" for c in name))


def _check_fields(meta: dict, folder: str | None, add) -> None:
    name = unicodedata.normalize("NFKC", frontmatter.text(meta, "name").strip())
    desc = frontmatter.text(meta, "description")
    if _not_text(meta, "name"):
        add("frontmatter-name", _not_text(meta, "name"))
    elif not _spec_name(name):
        add("frontmatter-name", "name must be 1-64 lowercase letters, digits and single hyphens, not starting or ending with a hyphen")
    else:
        if not NAME_RX.match(name):
            add("name-ascii", f"name '{name}' has letters outside a-z; claude.ai uploads and package_skill.py reject it")
        if "claude" in name or "anthropic" in name:
            add("name-reserved-word", "name must not contain 'claude' or 'anthropic'")
    if name and folder and name != unicodedata.normalize("NFKC", folder):
        add("name-matches-folder", f"name '{name}' must match its folder '{folder}'")
    if _not_text(meta, "description"):
        add("frontmatter-description", _not_text(meta, "description"))
    elif len(desc) > 1024:
        add("frontmatter-description", f"description is {len(desc)} characters; the limit is 1024")
    elif "<" in desc or ">" in desc:
        add("description-angle-brackets", "description must not contain < or >; Anthropic's packager rejects it")
    for key in sorted(set(meta) - SPEC_FIELDS - AGENT_FIELDS):
        add("unknown-field", f"'{key}' is neither an Agent Skills field nor one Claude Code documents; agents ignore it (put custom data under metadata)")
    if "compatibility" in meta and not (isinstance(meta["compatibility"], str) and 1 <= len(meta["compatibility"]) <= 500):
        add("field-compatibility", "compatibility must be a string of 1-500 characters")
    md = meta.get("metadata")
    if "metadata" in meta and not (isinstance(md, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in md.items())):
        add("field-metadata", "metadata must map string keys to string values (quote numbers like \"1.0\")")
    if "allowed-tools" in meta and not isinstance(meta["allowed-tools"], str):
        add("field-allowed-tools", "allowed-tools should be one space-separated string")
    if "license" in meta and not isinstance(meta["license"], str):
        add("field-license", "license should be a short string or the name of a bundled license file")
    for key, allowed in CLAUDE_CODE_VALUES.items():
        if key in meta and (type(meta[key]), meta[key]) not in {(type(a), a) for a in allowed}:  # 0 is not False
            shown = " or ".join(str(a).lower() for a in allowed)
            add("field-claude-code", f"{key} is {meta[key]!r}; Claude Code accepts {shown}")
    listed = len(desc) + len(frontmatter.text(meta, "when_to_use"))
    if listed > LISTING_MAX:
        add("listing-length", f"description and when_to_use are {listed} characters; Claude Code cuts the listing at "
                              f"{LISTING_MAX}, so put the key use case first")
    if folder and (folder.lower() == "synced" or folder.startswith("anthropic-skills")):
        add("folder-reserved", f"Claude Code does not load a skill folder named '{folder}'; rename it")


def lint_text(text: str, path: str = "<text>", folder: str | None = None) -> list[Finding]:
    out: list[Finding] = []

    def add(rule_id, msg):
        out.append(_finding(path, rule_id, msg))

    try:
        meta, body = frontmatter.split(text)
    except ValueError as e:  # the field rules would only repeat "missing", so report the cause once
        add("frontmatter", str(e))
        meta, body = {}, text
    else:
        _check_fields(meta, folder, add)
    name, desc = frontmatter.text(meta, "name"), frontmatter.text(meta, "description")
    # ponytail: rough token estimate (4 ASCII characters or 1 other character per token); a tokenizer would be exact.
    tokens = int(sum(0.25 if ord(c) < 128 else 1 for c in body))
    if tokens > 5000:  # the spec recommends under 5000 tokens for instructions
        add("body-tokens", f"instructions are about {tokens} tokens; keep SKILL.md under ~5000 and move detail to references/")
    if len(text.splitlines()) > 500:
        add("length", "SKILL.md over 500 lines; move detail into reference files")
    for rule_id, _, rx, msg, _ in PATTERNS:
        if rx.search(body):
            add(rule_id, msg)
    if re.search(r"(?i)\breview", name + " " + desc) and REVIEW_FILTER.search(body):
        add("review-filtering", "Review instructions that filter by severity cut recall on current models; report all and filter later.")
    if sum(1 for line in prose(body).splitlines() if SHOUT.search(line)) > 5:
        add("shouting", "Explain why instead of capitalized MUST/NEVER; current models overreact to aggressive emphasis.")
    return out


LINK = re.compile(r"\]\((?:<([^>\n]+)>|([^)\s]+))")
MENTION = re.compile(r"`((?:references|scripts|assets)/[^`\s]+)`")
CODE_SPAN = re.compile(r"(`+)(?!`).+?(?<!`)\1")


def _absent(refs, base: Path) -> list[str]:
    """Relative file paths among refs that do not exist under base; URLs, anchors and placeholders are skipped."""
    out = []
    for ref in refs:
        ref = unquote(ref.split("#")[0])
        if not ref or re.match(r"^[a-z]+:", ref) or ref.startswith(("/", "~")) or re.search(r"[<>{}*\[\]$]", ref):
            continue
        if "/" not in ref and "." not in ref:  # a bare word such as (URL) or (link) is a template placeholder
            continue
        if not (base / ref).exists():
            out.append(ref)
    return sorted(set(out))


def missing_references(body: str, base: Path) -> list[str]:
    """Files the body links to, outside code, that do not exist."""
    text = CODE_SPAN.sub("", prose(body))
    return _absent((m.group(1) or m.group(2) for m in LINK.finditer(text)), base)


def missing_mentions(body: str, base: Path) -> list[str]:
    """references/, scripts/ or assets/ paths named in inline code, outside code blocks, that do not exist."""
    return _absent((m.group(1) for m in MENTION.finditer(prose(body))), base)


def lint_file(path: Path) -> list[Finding]:
    path = Path(path)
    folder = path.parent.name if path.name == "SKILL.md" else None
    text = path.read_text(encoding="utf-8", errors="replace")
    out = lint_text(text, str(path), folder)
    body = frontmatter.parse(text)[1]
    for ref in missing_references(body, path.parent):
        out.append(_finding(path, "missing-reference", f"links to '{ref}', which does not exist"))
    for ref in missing_mentions(body, path.parent):
        out.append(_finding(path, "missing-mention", f"names '{ref}', which does not exist; link it if the skill ships it"))
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


# Reserved marketplace names (marketplace reference, "Reserved names"); other spellings count too.
RESERVED = {"claude-code-marketplace", "claude-code-plugins", "claude-plugins-official", "anthropic-marketplace",
            "anthropic-plugins", "agent-skills", "anthropic-agent-skills", "life-sciences", "knowledge-work-plugins",
            "claude-for-legal", "claude-for-financial-services", "financial-services-plugins", "first-party-plugins",
            "claude-tag-plugins", "claude-community", "claude-plugins-community", "healthcare",
            "anthropic-plugin-directory", "claude-plugin-directory", "inline", "builtin", "skills-dir", "synced",
            "claude-plugin-test", "npm", "pip", "uv", "cargo", "github", "gh"}


def _reserved(name: str) -> bool:
    spelled = re.sub(r"[^\w]", "-", name.lower().rstrip("."))  # claude.code.plugins is claude-code-plugins
    return (spelled in RESERVED or spelled.startswith("claudeai-")
            or any(w in spelled for w in ("anthropic", "official")))


def lint_marketplace(path: Path) -> list[Finding]:
    """.claude-plugin/marketplace.json, as the Claude Code validator checks it."""
    path = Path(path)
    out: list[Finding] = []

    def add(rule_id, msg):
        out.append(_finding(path, rule_id, msg))

    doc, why = _load_manifest(path)
    if why:
        add("manifest-json", why)
        return out
    for key in ("name", "owner", "plugins"):
        if key not in doc:
            add("marketplace-field", f"missing required field '{key}'")
    owner = doc.get("owner")
    if "owner" in doc and not (isinstance(owner, dict) and isinstance(owner.get("name"), str) and owner["name"].strip()):
        add("marketplace-field", "owner must be an object with a non-empty name")
    plugins = doc.get("plugins", [])
    if not isinstance(plugins, list):
        add("marketplace-field", "plugins must be a list of plugin entries")
        plugins = []
    root = isinstance(doc.get("metadata"), dict) and doc["metadata"].get("pluginRoot")
    seen = set()
    for i, p in enumerate(plugins):
        if not isinstance(p, dict):
            add("marketplace-plugin", f"plugins[{i}] must be an object with name and source")
            continue
        for key in ("name", "source"):
            if key not in p:
                add("marketplace-plugin", f"plugins[{i}] is missing '{key}'")
        pname = p.get("name")
        if isinstance(pname, str) and not PLUGIN_ID.match(pname):
            add("marketplace-plugin", f"plugins[{i}].name {pname!r} may use only ASCII letters, digits, '.', '_' and '-', "
                                      "starting with a letter or digit")
        if isinstance(pname, str) and len(pname) > DESKTOP_MAX:
            add("marketplace-desktop", f"plugins[{i}].name is {len(pname)} characters; Claude Desktop drops entries over "
                                       f"{DESKTOP_MAX}")
        if isinstance(pname, str) and pname in seen:
            add("marketplace-plugin", f"duplicate plugin name '{pname}'")
        seen.add(pname if isinstance(pname, str) else None)
        src = p.get("source")
        for why in _source_problems(src) if "source" in p else []:
            add("marketplace-source", f"plugins[{i}].source: {why}")
        if "headersHelper" in p and p.get("strict") is not False:
            add("marketplace-source", f"plugins[{i}] sets headersHelper, which needs \"strict\": false")
        if isinstance(src, str) and ".." in Path(src).parts:
            add("marketplace-source", f"plugins[{i}].source '{src}' must not leave the marketplace with '..'")
        elif isinstance(src, str) and src != "." and not src.startswith("./") and not root:
            add("marketplace-source", f"plugins[{i}].source '{src}' is a relative path and must start with ./")
    name = doc.get("name", "")
    if "name" in doc and (not isinstance(name, str) or not PLUGIN_ID.match(name) or ".." in name):
        add("marketplace-name", f"marketplace name {name!r} may use only ASCII letters, digits, '.', '_' and '-', "
                                "starting with a letter or digit and without '..' (a non-ASCII name counts as "
                                "impersonating an official marketplace)")
    elif name in DESKTOP_RESERVED or len(name) > DESKTOP_MAX:
        add("marketplace-desktop", f"Claude Desktop rejects the marketplace name '{name[:40]}': reserved there, or over "
                                   f"{DESKTOP_MAX} characters")
    elif isinstance(name, str) and _reserved(name):
        add("marketplace-reserved", f"marketplace name '{name}' is reserved for or looks like an official Anthropic "
                                    "marketplace; adding it fails unless it is hosted under github.com/anthropics")
    meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    if not (isinstance(doc.get("description"), str) and doc["description"].strip()
            or isinstance(meta.get("description"), str) and meta["description"].strip()):
        add("marketplace-description", "add a description so people know what the marketplace offers")
    if doc.get("plugins") == []:
        add("marketplace-empty", "the marketplace lists no plugins")
    return out


SOURCE_TYPES = {"github": ("repo",), "url": ("url",), "git-subdir": ("url", "path"), "npm": ("package",),
                "archive": ("url",), "command": ("command",)}
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9A-Fa-f]{64}\Z")


def _source_problems(src) -> list[str]:
    """What the marketplace reference ("Plugin sources") rejects in an entry's source object; strings are checked apart."""
    if isinstance(src, str):
        return []
    if not isinstance(src, dict):
        return ["must be a relative path or an object"]
    kind = src.get("source")
    if kind not in SOURCE_TYPES:
        return [f"unknown source type {kind!r}; use one of {', '.join(SOURCE_TYPES)}"]
    out = [f"{kind} needs a non-empty string '{k}'" for k in SOURCE_TYPES[kind]
           if not (isinstance(src.get(k), str) and src[k].strip())]
    if out:
        return out
    if kind == "github" and not re.fullmatch(r"[\w.-]+/[\w.-]+", src["repo"]):
        out.append(f"repo {src['repo']!r} is not owner/repo")
    if kind == "url" and not src["url"].startswith(("https://", "http://", "file://", "git@")):
        out.append(f"url {src['url']!r} must be a full git URL (https://, http://, file:// or git@)")
    if kind == "git-subdir" and ".." in src["path"].replace("\\", "/").split("/"):
        out.append("path must not contain '..'")
    if kind == "npm" and ".." in src["package"]:
        out.append("package must not contain '..'")
    if kind == "archive" and not src["url"].startswith("https://"):
        out.append("an archive url must use https://")
    if kind == "archive" and "sha256" in src and not SHA256.match(str(src["sha256"])):
        out.append("sha256 must be 64 hex characters")
    if kind in ("github", "url", "git-subdir") and "sha" in src and not SHA1.match(str(src["sha"])):
        out.append("sha must be a full 40-character lowercase commit SHA")
    if kind == "command":
        cmd = src["command"]
        if not (cmd.isascii() and cmd.isprintable()) or len(cmd) > 500 or "    " in cmd:
            out.append("command must be printable ASCII, at most 500 characters, without a run of four spaces")
        t = src.get("timeout", 60)
        if not (isinstance(t, int) and not isinstance(t, bool) and 1 <= t <= 600):
            out.append("timeout must be a whole number of seconds from 1 to 600")
        if src.get("mode", "copy") not in ("copy", "link"):
            out.append("mode must be copy or link")
    return out


DESKTOP_MAX = 128
DESKTOP_RESERVED = {"org", "org-provisioned", "unknown"}
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


# Each half of a plugin id (plugin@marketplace), as Claude Code installs it (marketplace reference, "Plugin entries").
PLUGIN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
# What Claude Code rejects in a plugin or marketplace name: whitespace, @ and :, path separators, control and bidi characters.
BAD_NAME_CHARS = re.compile(r"[\s@:/\\\x00-\x1f\x7f\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def _load_manifest(path: Path):
    """(object, None) for a JSON object, else (None, why)."""
    import json

    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        return None, f"invalid JSON: {e}"
    return (doc, None) if isinstance(doc, dict) else (None, "the manifest must be a JSON object")


def lint_plugin(path: Path) -> list[Finding]:
    """.claude-plugin/plugin.json, as Claude Code's plugins reference describes it."""
    path = Path(path)
    doc, why = _load_manifest(path)
    if why:
        return [_finding(path, "manifest-json", why)]
    out = []
    name = doc.get("name")
    if not isinstance(name, str) or not name or BAD_NAME_CHARS.search(name):
        out.append(_finding(path, "plugin-name", f"plugin name {name!r} must be a non-empty string without spaces, @, :, "
                                                 "slashes or control characters"))
    elif not NAME_RX.match(name):
        out.append(_finding(path, "plugin-name-style", f"plugin name '{name}' is not kebab-case (my-plugin)"))
    if "version" in doc and not SEMVER.match(str(doc["version"])):
        out.append(_finding(path, "plugin-version", f"version '{doc['version']}' is not semantic (x.y.z)"))
    if not doc.get("description"):
        out.append(_finding(path, "plugin-description", "add a description so people know what the plugin does"))
    return out


def health(installed) -> dict[str, dict]:
    """Lint every installed skill file and summarize by source: {source: {skills, errors, warnings, worst}}."""
    report: dict[str, dict] = {}
    for inst in installed:
        path = Path(inst.path)
        if not path.is_file():  # built-in skills have no file
            continue
        src = inst.id.split("/")[0]
        row = report.setdefault(src, {"skills": 0, "errors": 0, "warnings": 0, "worst": []})
        row["skills"] += 1
        found = lint_file(path)
        errs = [f for f in found if f.severity == "error"]
        row["errors"] += len(errs)
        row["warnings"] += len(found) - len(errs)
        if errs:
            row["worst"].append(f"{inst.invoke}: {errs[0].rule}")
    return dict(sorted(report.items()))
