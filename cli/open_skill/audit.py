"""Heuristic security review of skill folders: SKILL.md, references, scripts and assets.

It flags text a person should read before trusting a skill. A clean report means no rule matched,
not that the skill is safe. Files are only read as text; nothing is run or changed.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

DISCLAIMER = "heuristic review: every finding needs a human look, and a clean report does not mean a skill is safe"
SEVERITIES = ("high", "medium", "low")
ANTHROPIC_SKILLS = "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#security-considerations"


@dataclass
class Finding:
    severity: str
    rule: str
    file: str
    line: int
    excerpt: str
    source: str
    message: str


@dataclass
class Rule:
    id: str
    severity: str
    pattern: re.Pattern | None  # None for rules checked per file rather than per line
    message: str
    source: str
    whole: bool = False  # match across lines; the finding points at the line where the match starts
    only: re.Pattern | None = None  # when set, the rule applies only to file paths this matches
    unless: re.Pattern | None = None  # a line match is skipped when the text before it on the line matches this
    frontmatter: bool = False  # a line rule that applies only inside the file's leading YAML frontmatter


RULES: dict[str, Rule] = {}


def rule(id: str, severity: str, pattern: str | None, message: str, source: str, whole: bool = False,
         only: str | None = None, unless: str | None = None, frontmatter: bool = False) -> None:
    """Register a rule; every rule cites the public guidance it comes from. Patterns ignore case."""
    assert severity in SEVERITIES and id not in RULES, id
    flags = re.IGNORECASE | (re.DOTALL if whole else 0)
    RULES[id] = Rule(id, severity, re.compile(pattern, flags) if pattern else None, message, source, whole,
                     re.compile(only, re.IGNORECASE) if only else None,
                     re.compile(unless, re.IGNORECASE) if unless else None, frontmatter)


def _applies(r: Rule, file: str) -> bool:
    return r.only is None or file == "<text>" or bool(r.only.search(file))


# Characters an excerpt shows escaped: zero-width space, word joiners, bidi overrides and isolates, Unicode tag
# characters, the soft hyphen, the Mongolian vowel separator, Hangul fillers and variation selectors (the hidden-unicode
# rule flags a narrower set). ponytail: ZWJ/ZWNJ, LRM/RLM and the emoji selectors FE0E/FE0F stay unescaped so emoji and
# right-to-left text read normally; add them if hidden payloads start using those.
INVISIBLE = re.compile(r"[\u00ad\u115f\u1160\u180e\u200b\u202a-\u202e\u2060-\u2064\u2066-\u2069\u3164\ufe00-\ufe0d"
                       r"\uffa0\U000e0000-\U000e007f\U000e0100-\U000e01ef]")


def _escape(c: str) -> str:
    n = ord(c)
    return f"\\x{n:02x}" if n < 256 else f"\\u{n:04x}" if n < 0x10000 else f"\\U{n:08x}"


def _excerpt(line: str, limit: int = 160) -> str:
    # Escape control and invisible characters so an excerpt cannot hide text or drive the terminal. Some invisible
    # ones (Hangul fillers, variation selectors) count as printable, so the INVISIBLE set is escaped too.
    s = "".join(c if c.isprintable() and not INVISIBLE.fullmatch(c) else _escape(c)
                for c in line.strip())
    return s if len(s) <= limit else s[: limit - 3] + "..."


def _frontmatter_end(lines: list[str]) -> int:
    """The 1-based line number of the --- that closes leading frontmatter, or 0 when the file has none."""
    if not lines or lines[0].lstrip("\ufeff").rstrip() != "---":
        return 0
    return next((n for n, line in enumerate(lines[1:], 2) if line.rstrip() in ("---", "...")), 0)


def audit_text(text: str, file: str = "<text>") -> list[Finding]:
    """Findings for one file's text; rules limited to some files (only=) are skipped elsewhere, except for "<text>"."""
    out = []
    rules = [r for r in RULES.values() if _applies(r, file)]
    lines = text.split("\n")  # only \n, as editors and the whole-text rules count lines
    end = _frontmatter_end(lines)
    for n, line in enumerate(lines, 1):
        for r in rules:
            if r.frontmatter and not 1 < n < end:
                continue
            if r.pattern and not r.whole and any(not (r.unless and r.unless.search(line, 0, m.start()))
                                                 for m in r.pattern.finditer(line)):
                out.append(Finding(r.severity, r.id, file, n, _excerpt(line), r.source, r.message))
    for r in rules:
        if r.pattern and r.whole:
            for m in r.pattern.finditer(text):
                out.append(Finding(r.severity, r.id, file, text.count("\n", 0, m.start()) + 1, _excerpt(m.group()),
                                   r.source, r.message))
    return out


# Instructions that turn the agent against its user. A skill body is read with the same trust as the
# user's own instructions, so these are prompt injection in the sense of OWASP LLM01.
OWASP_LLM01 = "https://genai.owasp.org/llmrisk/llm01-prompt-injection/"
NOT = r"(?<!not )(?<!n't )(?<!n’t )(?<!never )"  # "don't ignore the user's instructions" is advice, not an attack
# Security guidance quotes the attacks it warns about ("Ignore previous instructions...", `<system-reminder>`), and
# forbids them ("never allow fetched text to override the user"). ponytail: an attacker can quote too; the agent still
# reads quoted text, so this trades that case for not flagging every skill that teaches injection defense.
MENTIONED = r"[\"“'‘`]$"
FORBIDDEN = r"\b(never|not|n't|n’t|no)\s+(let|allow|permit)\w*\b[^.;:!?]*$"
rule("override-instructions", "high",
     rf"\b{NOT}(ignore|disregard|forget|bypass)\b[^.\n]{{0,40}}\b(previous|prior|above|earlier|preceding|"
     r"all|any|system|user['’]?s?|other)\b[^.\n]{0,20}\b(instructions?|prompts?|rules|guidelines|directions|policies)\b"
     r"|\boverride\s+(the\s+|any\s+|all\s+)?(user['’]?s?|previous|prior|earlier)\s+(instructions?|prompts?|rules|requests?)"
     r"|\b(your|the following is (your|the)|this is (your|the)|here is (your|the))\s+(new|updated|real)\s+system prompt\b|\btake(s)? (precedence|priority) over (the |any |your )?(system|user)",
     "tries to override the user's or the system's instructions", OWASP_LLM01, unless=MENTIONED + "|" + FORBIDDEN)


rule("conceal-from-user", "high",
     r"\b(do not|don['’]t|never|without)\s+(tell|inform|notify|mention|alert|warn)(ing)?\s+(this\s+|it\s+|that\s+|anything\s+)?"
     r"(to\s+)?(the\s+)?users?\b(?!\s+(that\s+)?(they|you)\b|\s+to\b)|\bhide\s+(this|it|that|the\s+\w+)\s+from\s+the\s+user|\bthe\s+user\s+(must|should|will)"
     r"\s*(not|n't|n’t|never)\s+(know|see|notice|find out)|" + NOT + r"\bsilently\s+(run|execute|install|download|send|upload|delete|post)",
     "asks the agent to hide what it does from the user", ANTHROPIC_SKILLS)


OWASP_LLM06 = "https://genai.owasp.org/llmrisk/llm062025-excessive-agency/"
rule("disable-confirmation", "high",
     r"\b(do not|don['’]t|never|no need to|without)\s+(ask|wait|prompt|check)(ing)?\s+(the\s+user\s+)?(for\s+)?"
     r"(permission|confirmation|approval|consent)|" + NOT + r"\bskip\s+(the\s+|all\s+|any\s+)?(confirmation|approval|permission)s?\b"
     r"|\bauto-?approve\s+(all|every|any)\b"
     r"|\b(the\s+user\s+has|you\s+have)\s+(already\s+(pre-?)?|pre-?)(approved|authori[sz]ed|consented)",
     "tells the agent to act without the user's approval, or claims approval was already given", OWASP_LLM06)


PERMISSION_MODES = "https://code.claude.com/docs/en/permission-modes"
rule("permission-bypass-flag", "medium",
     r"--dangerously-skip-permissions|\bbypassPermissions\b|--dangerously-bypass-approvals-and-sandbox|--yolo\b"
     r"|\bdanger-full-access\b|(--ask-for-approval|approval_policy|approval-policy)[\s=:\"']+never\b",
     "turns off the agent's permission prompts or sandbox; nothing then stops a harmful command", PERMISSION_MODES)


ATTACK_CRED_FILES = "https://attack.mitre.org/techniques/T1552/001/"
rule("secret-files", "medium",
     r"(~|\$HOME|\$\{HOME\}|%USERPROFILE%)[/\\]\.ssh\b|\bid_(rsa|dsa|ecdsa|ed25519)\b(?!\.pub)|\.aws[/\\](credentials|config)\b"
     r"|\.(netrc|pypirc|npmrc|git-credentials)\b|\.docker[/\\]config\.json|\.kube[/\\]config\b|\.gnupg\b"
     r"|application_default_credentials\.json|gcloud[/\\]credentials|\.config[/\\]gh[/\\]hosts\.yml|\.azure[/\\]\w*token",
     "points at SSH keys or cloud and package-registry credentials; a skill rarely needs to read them", ATTACK_CRED_FILES)


# Writing one ("copy .env.example to .env", "cat > .env") is ordinary setup, so a .env that is the target is skipped.
rule("env-file-read", "medium",
     r"\b(cat|less|more|head|tail|type|read|print|dump|send|upload|post|copy|cp|scp|base64|xxd|curl)\b"
     r"(?![^\n]{0,40}\.env\.(example|sample|template))[^\n]{0,40}"  # copying a template writes .env, it does not read it
     r"(?<![\w.-])(?<!to )(?<!to `)(?<!>)(?<!> )\.env(?!\.(example|sample|template))(\.[\w-]+)?\b",
     "reads or sends a .env file, which usually holds API keys and passwords", ATTACK_CRED_FILES)


rule("credential-store", "high",
     r"\bsecurity\s+(find-generic-password|find-internet-password|dump-keychain)\b|\blogin\.keychain|\bsecret-tool\s+(lookup|search)\b"
     r"|\bcmdkey\s+/list\b|\bvaultcmd\b|\.password-store\b|\bkwallet-query\b",
     "reads the operating system's password store (Keychain, Secret Service, Windows Credential Manager)",
     "https://attack.mitre.org/techniques/T1555/")


rule("browser-data", "high",
     r"[/\\](?-i:Login Data|Web Data|Local State)\b|\b(logins\.json|key[34]\.db|cookies\.sqlite)\b|Google[/\\]Chrome[/\\]"
     r"|Microsoft[/\\]Edge[/\\]User Data|BraveSoftware[/\\]|\.mozilla[/\\]firefox|Firefox[/\\]Profiles|Library[/\\]Cookies",
     "reaches into browser profiles, where saved passwords and session cookies live",
     "https://attack.mitre.org/techniques/T1555/003/")


# Payloads found in malicious skills: a download run unread, a command hidden in an encoding, a known collection host.
# Every gap is bounded ({0,GAP}) so a long line costs linear time: a skill must not be able to stall its own audit.
GAP = 300
ATTACK_INGRESS = "https://attack.mitre.org/techniques/T1105/"
DOWNLOAD = r"\b(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b"
# An interpreter that reads its program from stdin: nothing after it, `-`, `-s`, or the end of the command.
# `| python -m json.tool` or `| node parse.js` only read data.
RUNNER = (r"(sudo\s+(-\w+\s+){0,4})?(env\s+)?(/(usr/)?(local/)?bin/)?"
          r"((ba|z|da|k|fi)?sh|python[23]?|node|perl|ruby|php|iex|Invoke-Expression|pwsh|powershell)"
          r"(?=\s*($|[;&|)\"'`])|\s+-s?(\s|$))")
rule("remote-exec", "medium",
     rf"{DOWNLOAD}[^|\n]{{0,{GAP}}}\|\s*{RUNNER}|(\b(ba|z)?sh|\bsource|(^|\s)\.)\s+<\(\s*{DOWNLOAD}"
     rf"|\b(ba|z)?sh\s+-c\s+[\"']?\$\(\s*{DOWNLOAD}|\b(iex|Invoke-Expression)\b[^\n]{{0,{GAP}}}\(\s*{DOWNLOAD}"
     rf"|\b(exec|eval)\s*\([^\n]{{0,{GAP}}}\burlopen\(",
     "downloads a script and runs it at once, so nobody reads what runs; download it, read it, then run it",
     ATTACK_INGRESS)


ATTACK_OBFUSCATION = "https://attack.mitre.org/techniques/T1027/"
DECODE = r"\b(base(32|64)|xxd)\s+(-\w*[dDr]\w*|--decode)\b"  # base64 -d, -di, -D, --decode; xxd -r
rule("encoded-exec", "high",
     rf"{DECODE}[^\n]{{0,{GAP}}}\|\s*" + RUNNER
     + rf"|\beval\s*[\"'(]?\s*[\"']?\$\(\s*(echo|printf)\b[^)\n]{{0,{GAP}}}\|\s*{DECODE}|\beval\s*[\"'(]?\s*[\"']?\$\(\s*{DECODE}"
     rf"|\b(exec|eval)\s*\([^\n]{{0,{GAP}}}\b(b64decode|b32decode|decodebytes|fromhex|codecs\.decode)\b"
     rf"|\bFromBase64String\b[^\n]{{0,{GAP}}}\b(iex|Invoke-Expression)\b"
     rf"|\b(iex|Invoke-Expression)\b[^\n]{{0,{GAP}}}\bFromBase64String\b"
     rf"|\b(powershell|pwsh)(\.exe)?\b[^\n]{{0,{GAP}}}\s-(e|ec|enc|encodedcommand)\s+[A-Za-z0-9+/=]{{16}}",
     "decodes text and runs it as a command; the encoding hides what runs from a reviewer", ATTACK_OBFUSCATION)


# Services built to receive requests from strangers. ponytail: chat webhooks (Discord, Telegram bots) and file drops
# are left out because notification and sharing skills use them openly; add them if stolen data starts going there.
ATTACK_EXFIL_WEB = "https://attack.mitre.org/techniques/T1567/"
rule("exfil-endpoint", "high",
     r"\b(webhook\.site|requestbin\.(com|net)|[\w-]{1,63}\.m\.pipedream\.net|interact\.sh|oast\.(fun|pro|live|site|online|me)"
     r"|burpcollaborator\.net|oastify\.com|canarytokens\.com|pastebin\.com/api)\b",
     "names a request-collection or paste service that attackers use to receive stolen data", ATTACK_EXFIL_WEB)


# Memory and context poisoning: a skill that writes the agent's user-level instructions (~/.claude/CLAUDE.md,
# ~/.codex/AGENTS.md, a MEMORY.md) or its settings (permissions, hooks, MCP servers) plants text or grants that
# outlive the skill and apply to every later session. A project's own AGENTS.md or CLAUDE.md is left out: editing it is
# ordinary work that shows up in review. ponytail: the shell forms and a few verbs are covered; add more if needed.
OWASP_AGENTIC = "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/"
HOME = r"(~|\$HOME|\$\{HOME\}|\$USERPROFILE|\$env:USERPROFILE|%USERPROFILE%)[/\\]"
AGENT_SETTINGS = (r"\.claude[/\\]settings(\.local)?\.json|\.codex[/\\]config\.toml|\.gemini[/\\]settings\.json"
                  r"|\.cursor[/\\]mcp\.json")
PATHCHARS = r"[^\s\"'`|;&<>]"
USER_TARGET = rf"[\"'`]?{HOME}{PATHCHARS}{{0,120}}?(\b(CLAUDE|AGENTS|GEMINI|MEMORY)(\.local)?\.md\b|{AGENT_SETTINGS})"
ANY_TARGET = rf"({USER_TARGET}|[\"'`]?{PATHCHARS}{{0,120}}?({AGENT_SETTINGS}))"
ARG = r"(\s+(\"[^\"\n]{0,300}\"|'[^'\n]{0,300}'|[^\s|;&]+))"  # one shell argument
# Shell writes reach project settings too (a project's .claude/settings.json can grant permissions and hooks);
# prose only counts for the user's own files, since setup docs routinely say "add the server to .cursor/mcp.json".
rule("agent-config-write", "medium",
     rf"((?<![-=>])>>?|\btee\s+(-a\s+|--append\s+)?)\s*{ANY_TARGET}"
     rf"|\b(cp|mv|ln|install)\b(\s+-[-\w]+)*{ARG}{{1,3}}?\s+{ANY_TARGET}"
     rf"|\bsed\s+(-\w+\s+)*-i\S*{ARG}{{1,3}}?\s+{ANY_TARGET}"
     rf"|\b(Add-Content|Set-Content|Out-File)\b(\s+-\w+)*\s+{ANY_TARGET}"
     rf"|\b(append|add|write|insert|save|put)\b[^.\n]{{0,80}}?\b(to|into|in)\s+((your|the|a|my)\s+)?{USER_TARGET}"
     rf"|\b(update|edit|modify|change|overwrite|replace)\s+((your|the|a|my)\s+)?{USER_TARGET}",
     "writes the agent's user-level instructions, memory or settings, which then apply to every later session; a "
     "skill that changes them can plant instructions or grant itself permissions", OWASP_AGENTIC)


# Tokens in the shape their issuers publish. Placeholders are skipped: AWS's documented example key (AKIA...EXAMPLE)
# and a body that starts with a filler (xxxxxxxx, 00000000, aaaaaaaa, ********, YOUR...). A key header only counts at a line's start,
# so prose that names the header ("starts with -----BEGIN ...") is left alone.
ATTACK_CRED_IN_FILES = "https://attack.mitre.org/techniques/T1552/001/"
REAL = r"(?!x{8}|0{8}|a{8}|\*{8}|your)"  # patterns ignore case, so x{8} also skips XXXXXXXX
rule("hardcoded-secret", "high",
     rf"\bsk-ant-(api|admin)\d{{2}}-{REAL}[A-Za-z0-9_-]{{20}}|\bsk-(proj|svcacct|admin)-{REAL}[A-Za-z0-9_-]{{40}}"
     rf"|\bgh[pousr]_{REAL}[A-Za-z0-9]{{36}}\b|\bgithub_pat_{REAL}[A-Za-z0-9_]{{60}}"
     rf"|\b(AKIA|ASIA)(?![0-9A-Z]{{0,12}}EXAMPLE){REAL}[0-9A-Z]{{16}}\b|\bxox[abpr]-[0-9]{{6,15}}-{REAL}[A-Za-z0-9-]{{6}}"
     rf"|\bAIza{REAL}[0-9A-Za-z_-]{{35}}\b|\b[rs]k_live_{REAL}[0-9A-Za-z]{{20}}|\bnpm_{REAL}[A-Za-z0-9]{{36}}\b"
     rf"|\bglpat-{REAL}[A-Za-z0-9_-]{{20}}\b|^[\s\"'`>]*-----BEGIN (RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY( BLOCK)?-----",
     "contains what looks like a real API token or private key; anyone who installs the skill can read and use it",
     ATTACK_CRED_IN_FILES)


# Characters that are invisible wherever they appear, and a run of variation selectors: one selector after a base
# character picks a glyph (emoji, CJK variants), several in a row carry bytes ("emoji smuggling").
HIDDEN = (r"[\u115f\u1160\u200b\u202a-\u202e\u2060-\u2064\u2066-\u2069\u3164\uffa0\U000e0000-\U000e007f]"
          r"|[\ufe00-\ufe0f\U000e0100-\U000e01ef]{2}")
rule("hidden-unicode", "high", HIDDEN + r"|(?<!^)\ufeff",
     "contains invisible or direction-changing characters that can hide instructions from a human reviewer", OWASP_LLM01)


# Markdown hides HTML comments when rendered, so a reviewer reading the page never sees them; the agent does.
# Keywords must stand alone: <!-- prettier-ignore --> and <!-- simplify-ignore-start --> are tool directives.
rule("hidden-comment", "medium",
     r"<!--(?:(?!-->|<!--).){0,2000}?(?<![\w-])(ignore|disregard|exfiltrat\w*|(do not|don't|without)\s+tell\w*|(ai|llm)\s+(agents?|assistants?|models?)"
     r"|assistant|you\s+(are|must|should)|curl|wget|base64)(?![\w-])",
     "an HTML comment, invisible once rendered, speaks to the agent or carries a command", OWASP_LLM01, whole=True,
     only=r"\.(md|mdx|markdown|html?)$")


rule("fake-authority", "high",
     r"\b(message|notice|instructions?|update|directive|order)\s+from\s+(anthropic|openai|the\s+system|the\s+(administrator|admin)"
     r"|your\s+(developers?|creators?|operators?))\b|\[\s*(system|admin|developer)\s*(message|override|notice|prompt)\s*\]"
     r"|</?system-reminder>|<\|im_start\|>|<\|(system|start_header_id)\|>",
     "impersonates the system, the agent vendor or an administrator to gain authority over the agent", OWASP_LLM01,
     unless=MENTIONED)


# allowed-tools pre-approves tools for the turn that invokes the skill, whether or not the folder is trusted.
BROAD_BASH = r"""(Bash["']?[ \t]*(,|$)|Bash\b(?![("'])|Bash\(\s*\*\s*\)|Bash\((curl|wget|sudo|rm|sh|bash|eval|python3?|node)\b)"""
rule("broad-allowed-tools", "medium",
     # on the key's line, or on the indented lines under it (a YAML list, or a folded > or literal | scalar)
     rf"(?m)^allowed-tools[ \t]*:[^\n]*?{BROAD_BASH}|^allowed-tools[ \t]*:[ \t]*([>|][+-]?)?[ \t]*\r?\n(?:[ \t]+[^\n]*\n)*?[ \t]+[^\n]*?{BROAD_BASH}",
     "allowed-tools pre-approves any shell command, or a download, delete or interpreter command, without a prompt",
     "https://code.claude.com/docs/en/skills#pre-approve-tools-for-a-skill", whole=True)


rule("skill-hooks", "medium", r"^(?-i:hooks)[ \t]*:",  # YAML keys are case-sensitive
     "registers hooks when the skill or agent is invoked; their commands run on agent events for the rest of the "
     "session, long after the skill's own turn, so read every command they run",
     "https://code.claude.com/docs/en/hooks#hooks-in-skills-and-agents",
     only=r"(^|[/\\])(SKILL\.md|agents[/\\].+\.md)$", frontmatter=True)


rule("shell-at-load", "low", r"(^|\s)!`[^`]+`|^\s*```!",
     "runs a shell command while the skill loads, before the agent or the user sees the text; check what it runs",
     "https://code.claude.com/docs/en/skills#inject-dynamic-context", only=r"(^|[/\\])(SKILL\.md|commands[/\\][^/\\]+\.md)$")


def _files(root: Path):
    """Every file under root, links included but never followed, so a skill cannot point the audit elsewhere."""
    if not root.is_dir() or root.is_symlink():
        yield root
        return
    for d, dirs, names in os.walk(root):  # followlinks=False: linked folders are listed, not entered
        dirs[:] = sorted(x for x in dirs if x != ".git")
        yield from (Path(d, x) for x in sorted(names + [x for x in dirs if os.path.islink(os.path.join(d, x))]))


CWE_LINK = "https://cwe.mitre.org/data/definitions/59.html"
rule("link-outside-skill", "high", None,
     "a symbolic link points outside the skill folder; following it could read or run files the skill does not ship",
     CWE_LINK)

rule("native-executable", "medium", None,
     "a compiled program ships with the skill; it cannot be reviewed as text, so only run it from a source you trust",
     ANTHROPIC_SKILLS)
NATIVE = (b"\x7fELF", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe",
          b"\xca\xfe\xba\xbe", b"MZ")  # ELF, Mach-O (32/64-bit, both byte orders, universal), Windows PE
MAX_TEXT_BYTES = 5_000_000
rule("unscanned-file", "low", None, "text file too large to audit; review it by hand", ANTHROPIC_SKILLS)


def _flag(rule_id: str, path: Path, excerpt: str) -> Finding:
    r = RULES[rule_id]
    return Finding(r.severity, r.id, str(path), 0, _excerpt(excerpt), r.source, r.message)


def audit_file(path: Path, root: Path | None = None) -> list[Finding]:
    root = root or path.parent
    if path.is_symlink():  # never read through a link; a link inside the skill is audited at its target
        target = Path(os.path.realpath(path))
        inside = target.is_relative_to(Path(os.path.realpath(root)))
        return [] if inside else [_flag("link-outside-skill", path, f"-> {os.readlink(path)}")]
    if not path.is_file():  # sockets, FIFOs and devices: opening one could block or have side effects
        return []
    with path.open("rb") as fh:
        head = fh.read(8192)
    enc = "utf-16" if head[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"  # PowerShell writes UTF-16 with a BOM
    if enc == "utf-8" and b"\0" in head:  # binary: images and fonts are normal, programs deserve a look
        return [_flag("native-executable", path, head[:4].hex())] if head.startswith(NATIVE) else []
    if path.stat().st_size > MAX_TEXT_BYTES:
        return [_flag("unscanned-file", path, f"{path.stat().st_size} bytes")]
    data = path.read_bytes()
    return audit_text(data.decode(enc, errors="replace"), str(path))


def audit_paths(paths) -> list[Finding]:
    """Audit skill folders or single files; findings sorted most severe first."""
    out = []
    for p in paths:
        p = Path(os.path.realpath(p))  # a path the user names (often an installed link) is audited at its target
        out += [f for file in _files(p) for f in audit_file(file, p if p.is_dir() else p.parent)]
    return sorted(out, key=lambda f: (SEVERITIES.index(f.severity), f.file, f.line))


def summary(findings) -> dict[str, int]:
    return {s: sum(1 for f in findings if f.severity == s) for s in SEVERITIES}


def audit_installed(installed) -> dict[str, list[Finding]]:
    """Audit the folder of every installed skill that has one, grouped by source (built-ins have no files)."""
    folders: dict[str, set[str]] = {}
    for inst in installed:
        if Path(inst.path).is_file():
            folders.setdefault(inst.id.split("/")[0], set()).add(str(Path(inst.path).parent))
    return {src: audit_paths(sorted(dirs)) for src, dirs in sorted(folders.items())}
