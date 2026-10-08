<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/logo-dark.svg">
  <img src=".github/assets/logo.svg" alt="Open Skill Standard logo: a skill graph with one ordered route through it" width="72" height="72">
</picture>

# Open Skill Standard

**One router, one skill graph, 28 IT roles.** An open, agent-agnostic standard for choosing the right Agent Skills for a task, and a reference implementation that ties together superpowers, BMad Method, spec-kit, codegraph, Anthropic's skills and more, without copying any of them.

**English** · [Tiếng Việt](README.vi.md)

[Website](https://vokhoinhon.github.io/open-skill-standard/) · [Specification](spec/SPEC.md) · [Contributing](CONTRIBUTING.md)

<img src=".github/assets/route-data.svg" alt="Terminal: open-skill route --explain for a data engineer adding a warehouse pipeline returns an ordered, explained chain: writing-plans, subagent-driven-development, explore-data, code-review, with scores, runner-ups and the install command for each missing skill" width="790">

## Why

Coding agents now load skills from many independent projects. A typical setup has 100+ skills that overlap: three build workflows, several reviewers, two kinds of brainstorming. Two facts make that hard:

- Agents pick skills by matching descriptions, and overlapping descriptions make them load the wrong skill or miss the right one.
- Claude Code budgets the whole skill listing at about 1% of the context window and drops the descriptions of the least-used skills first ([docs](https://code.claude.com/docs/en/skills)), so matching gets worse exactly when you install more.

Open Skill Standard adds the missing layer: metadata about **which role a skill serves, which phase it acts in, and which artifacts it consumes and produces**. From that, a router builds a short, ordered, explained chain for each task.

## What you get

| Part | What it does |
|---|---|
| `open-skill-router` skill | Entry point: routes the task, announces the chain in one line, runs step 1, records what ran |
| `open-skill-standards` skill | Definition-of-done checklists, general and for each role |
| `open-skill-intel` skill | Sends each question to the best source: codegraph, Context7, schemas, the web, your notes, the skill graph |
| `open-skill-learn` skill | Remembers your lessons and preferences so future routes use them |
| `open-skill` CLI | `route`, `search`, `scan`, `doctor`, `build`, `validate`, `lint`, `init`, `learn`, `feedback`… |
| Registry | 18 adapters describing 190+ upstream skills and tools, 28 role packs, 9 model profiles |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/architecture-dark.svg">
  <img src=".github/assets/architecture.svg" alt="Architecture: the public registry and organization overlays feed scan and a SQLite FTS5 index; the router combines them with your project and your local ~/.open-skill layer, and the coding agent runs the chain" width="960">
</picture>

## Quick start

```bash
# 1. Install the skills (Claude Code) — or: npx skills add VoKhoiNhon/open-skill-standard -g, or see "Any agent" below
/plugin marketplace add VoKhoiNhon/open-skill-standard
/plugin install open-skill@open-skill-standard

# 2. Tell it your role(s); this also seeds starter knowledge for them
uvx --from git+https://github.com/VoKhoiNhon/open-skill-standard@v0.7.4 open-skill init --role data-engineer=0.7 --role data-analyst=0.3

# 3. In your agent, inside any project
/open-skill-router add a pipeline that loads orders into the warehouse
```

`open-skill doctor` shows which frameworks are installed and the official command for each one that is missing. In a project where `npx skills` keeps a `skills-lock.json`, it also says which of those skills were edited since install or are no longer in a skill folder.

## Any agent that loads Agent Skills

The skills follow the [Agent Skills](https://agentskills.io) format, so they work in every agent that reads it. `registry/agents/` describes ten of them: where each loads skills, for the user and for a project, and how to tell it is installed. Every path cites the agent's documentation, or the line of [vercel-labs/skills](https://github.com/vercel-labs/skills) it comes from where the docs are silent.

| Agent | id | Installs to (user) | Installs to (project) |
|---|---|---|---|
| Claude Code | `claude-code` | `~/.claude/skills` | `.claude/skills` |
| Codex | `codex` | `~/.agents/skills` | `.agents/skills` |
| Cursor | `cursor` | `~/.cursor/skills` | `.agents/skills` |
| Gemini CLI | `gemini-cli` | `~/.gemini/skills` | `.agents/skills` |
| GitHub Copilot (CLI, coding agent, VS Code) | `github-copilot` | `~/.copilot/skills` | `.github/skills` |
| OpenCode | `opencode` | `~/.config/opencode/skills` | `.opencode/skills` |
| Goose | `goose` | `~/.agents/skills` | `.agents/skills` |
| Windsurf | `windsurf` | `~/.config/devin/skills` | `.devin/skills` |
| Amp | `amp` | `~/.config/agents/skills` | `.agents/skills` |
| Kiro | `kiro-cli` | `~/.kiro/skills` | `.kiro/skills` |

Each agent also reads other folders (Cursor, Copilot, OpenCode, Goose and Amp read Claude Code's, for example); `scan` knows them all and lists a skill once with every agent that sees it.

```bash
open-skill agents                                     # which agents are installed, what each sees
open-skill install open-skill-router --agent codex    # a core skill, or a path to any skill folder
open-skill install ./my-skill --agent cursor --project . --symlink
open-skill route "<task>" --agent codex               # only skills Codex sees, by the names Codex calls them
open-skill update                                     # core skills you installed, at this CLI's version
open-skill remove open-skill-router --agent codex
```

`install` never overwrites a skill it did not put there. It records every folder it creates, with a hash of each file, in `~/.open-skill/installed.json`; `remove` and `update` act only on those, and leave alone any file you changed or added.

## How routing works

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/routing-dark.svg">
  <img src=".github/assets/routing.svg" alt="Routing pipeline: request, phase and size, phase window, then for each phase candidate filters, scoring and selection, then trimming and the ordered steps" width="960">
</picture>

```text
registry (adapters, roles, models) ─┐
installed skills on this machine ───┼─► in-memory graph + SQLite FTS5 index
your profile, notes, history ───────┘
                       │
open-skill route "<task>" --project . --model <id>
  1. project state: .specify/ or _bmad/ (native framework), artifacts, role signals
  2. role mix → target phase → phase window (role packs can define their own)
  3. per phase: installed candidates, scored by role pack, role weights, text, artifact flow, your history
  4. rules: one build workflow; native framework wins; requirements met; model step limit
  5. output: chain + reasons + your applicable notes + missing skills + model notes
```

A real route (data engineer, spec-kit project without the speckit skills installed yet, Claude Opus 5.5):

```text
1. [plan]   superpowers:writing-plans               — primary for data-engineer; consumes spec
2. [build]  superpowers:subagent-driven-development — primary for data-engineer; consumes plan
3. [verify] data:explore-data                       — primary for data-engineer
4. [review] code-review                             — primary for data-engineer
missing: spec-kit/implement (not installed) → specify init --here --integration claude
missing: codegraph/impact (needs .codegraph in the project) → codegraph init
model note: Deliver what was asked at the intended scope; …
```

## See and question the graph

**Why this chain?** `route --explain` shows what decided the target phase, the size and the phase window, then each step with its score and up to three runner-ups:

```text
$ open-skill route "add a pipeline that loads orders" --role data-engineer --explain
target build from phase keywords: add, pipeline
size medium: no size keywords, the default
phase window: plan → build → verify → review (medium build task: starts at plan, then verify and review)
1. [plan] superpowers:writing-plans  score=2.5  — phase plan; role prior 2.00 (primary for data-engineer); text 1.00; consumes spec
2. [build] superpowers:subagent-driven-development  score=2.5  — …; consumes plan
   runner-ups: superpowers/test-driven-development 2.0, knowledge-work-data/write-query 0.9, knowledge-work-data/sql-queries 0.7
3. [verify] data:explore-data  score=2.0  — …
   runner-ups: knowledge-work-data/validate-data 2.0 (close call), open-skill/open-skill-standards 2.0, …
```

When no phase keyword matches, the phase line reads `phase: build (guessed, no signal)` and the JSON has `"phase_from": "guessed"`. An agent that has read the conversation should pass `--phase` (and `--size`) itself; keyword detection is the fallback.

**Why not that skill?** `--why-not` takes a skill id or invoke name and names the reason: not installed (with the install command), wrong phase or size, a requirement the project does not meet, a conflict with a chosen skill, a score below the minimum or below the winner's (both scores), the model's step limit, or a task small enough to do directly.

```text
$ open-skill route "add a pipeline that loads orders" --role data-engineer --why-not superpowers:executing-plans
superpowers/executing-plans is not in the chain for: add a pipeline that loads orders
  - [build] score 0.375 lost to superpowers/subagent-driven-development (2.5)
$ open-skill route "add a pipeline that loads orders" --role data-engineer --why-not superpowers/brainstorming
superpowers/brainstorming is not in the chain for: add a pipeline that loads orders
  - acts in discover, specify; this task's phase window is plan, build, verify, review
```

**What is there?** `search` filters by `--role`, `--phase`, `--source` and `--installed`; without a query it lists everything the filters keep:

```text
$ open-skill search --role data-engineer --phase verify --installed
      -  knowledge-work-data/explore-data
      -  knowledge-work-data/validate-data
      -  superpowers/test-driven-development
      …
```

**The whole graph.** `open-skill graph --format html --out graph.html` writes one self-contained page (no network access): skills by phase, each skill's artifacts, requirements, conflicts and recommending roles, an artifact table and the roles, with filters by role, phase, source and installed state and a search box. It works with the keyboard (`/` searches, `Esc` clears) and follows your light or dark theme. `--format json` and `--format mermaid` export the same graph for other tools.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/graph-viewer-dark.png">
  <img src=".github/assets/graph-viewer.png" alt="The skill graph page from open-skill graph --format html: skills grouped by phase, with filters by role, phase, source and installed state" width="960">
</picture>

## Parallel sessions

Several agent sessions can work on one project at once and share one [Graphify](https://github.com/Graphify-Labs/graphify) code graph. Each session declares the paths it works on. After an edit, `session update` refreshes the graph (Graphify locks and rewrites it, about 2.4 s on this repository) and lists the files within two steps of calls, references or imports of what changed since the session started, committed or not. It warns when one of them lies in another session's scope. It never blocks and never fails because of a conflict.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/sessions-dark.svg">
  <img src=".github/assets/sessions.svg" alt="Parallel sessions: sessions declare scopes and share one working tree and one Graphify graph; session update refreshes the graph, takes the files changed since the session started, sets aside other sessions' own edits, walks two hops back over calls, references and imports, and reports conflicts, others and affected files" width="960">
</picture>

```bash
uv tool install graphifyy && graphify extract . --code-only    # once per project
open-skill session start --scope "cli/open_skill/route.py" --task "speed up fit"
open-skill session start --scope "tests/**" --task "add fixtures for route tests"
open-skill session update --session <id>          # after an edit, from the session that made it
open-skill session list                           # --prune drops sessions idle for more than 6 hours
open-skill session end <id>
```

```text
$ open-skill session update --session a1b2c3
graph: 2204 nodes, 3566 edges (refreshed)
changed: cli/open_skill/route.py
affected: 14 files
  cli/open_skill/cli.py
  …
⚠ tests/test_route.py is in session b4c5d6 ("add fixtures for route tests"), reached from cli/open_skill/route.py
```

Graphify links `from pkg import mod` to the package, not to `mod.py`, and does not resolve `mod.fn()` as a call; `session update` resolves package imports itself, so a test that imports the module is still found. With `--session`, a changed file that lies only in another session's scope is counted as that session's work (listed with `·`), since sessions share one working tree. For call-level questions (callers, impact) keep codegraph. Session records live in `.open-skill/sessions/` inside the project, which ignores itself in git. `--json` gives the changed, affected and conflicting files to an agent.

## Roles

| Family | Roles |
|---|---|
| Engineering | frontend-developer, backend-developer, fullstack-developer, mobile-developer, embedded-engineer, game-developer |
| Quality & operations | qa-engineer, devops-engineer, site-reliability-engineer, cloud-engineer, security-engineer, database-administrator, system-administrator |
| Data & AI | data-engineer, analytics-engineer, data-analyst, data-scientist, ml-engineer, ai-engineer, data-ai-platform-engineer |
| Architecture & leadership | software-architect, tech-lead, engineering-manager |
| Product & delivery | product-manager, business-analyst, ux-designer, technical-writer, scrum-master |

Each role pack states the role's characteristic risk, its principles, the project files that suggest it, and its primary and alternative skills per phase. Readable playbooks are generated into [`skills/open-skill-router/references/roles/`](skills/open-skill-router/references/roles/README.md).

The same kind of request routes differently by role:

<img src=".github/assets/route-backend.svg" alt="Terminal: open-skill route --explain for a backend developer adding a CSV export endpoint, planned and built with backend skills" width="790">
<img src=".github/assets/route-sre.svg" alt="Terminal: open-skill route --explain for a site reliability engineer whose checkout requests time out, starting with debugging" width="790">

## Integrated frameworks

Adapters describe upstream skills as metadata and point to the official installers; nothing is vendored.

| Source | Role in the chain | License |
|---|---|---|
| [superpowers](https://github.com/obra/superpowers) | Execution discipline: design approval, plans, TDD, debugging, verification | MIT |
| [BMad Method](https://github.com/bmad-code-org/BMAD-METHOD) | Thinking partners, personas, planning artifacts, right-sized build (needs `bmad setup`) | MIT, trademark |
| [spec-kit](https://github.com/github/spec-kit) | Durable spec → plan → tasks → implement → converge (needs `specify init`) | MIT |
| [codegraph](https://github.com/colbymchenry/codegraph) | Code knowledge graph: call paths, impact, affected tests | MIT |
| [Graphify](https://github.com/Graphify-Labs/graphify) | Shared code graph for parallel sessions; refreshed by `open-skill session update` | Apache-2.0 |
| [Anthropic skills](https://github.com/anthropics/skills) | Documents, skill authoring, MCP servers, web testing, frontend design | per skill |
| [Knowledge-work plugins](https://github.com/anthropics/knowledge-work-plugins) | Data, engineering, product management, design | Apache-2.0 |
| [Context7](https://github.com/upstash/context7) | Current library documentation | MIT |
| [ponytail](https://github.com/DietrichGebert/ponytail) | Minimal solutions and over-engineering reviews | MIT |
| [taste-skill](https://github.com/leonxlnx/taste-skill) | Frontend visual quality | MIT |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | Engineering lifecycle: specs, task breakdown, thin slices, observability, hardening, migrations, launch | MIT |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | React, Next.js and React Native rules, UI and writing guideline reviews, Vercel deploys and cost tuning | MIT |
| Claude Code built-ins | code-review, security-review, run, claude-api, schedule… | — |

How the integrated frameworks chain: each phase's skills produce the artifacts the next phase consumes. `open-skill doctor` shows which sources are installed and the install command for the rest:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/lifecycle-dark.svg">
  <img src=".github/assets/lifecycle.svg" alt="Lifecycle graph: the 10 phases and 19 artifacts of the taxonomy, with the artifacts the skills in each phase produce and consume" width="960">
</picture>

<img src=".github/assets/doctor.svg" alt="Terminal: open-skill doctor listing each integrated source with installed and described skill counts and the install command for what is missing" width="790">

## Adapts to the model

Prompting advice changes between model generations; instructions that helped one model can hurt the next. Skills here stay model-neutral, and model-specific notes live in [`registry/models/`](registry/models/): effort per task size, chain length, short prompting notes and patterns to avoid, each with its source in Anthropic's prompting guides. An unknown future model falls back to its family, then to `generic`, so nothing breaks; a weekly workflow opens an issue when the guides list a model without a profile. `open-skill lint` rejects patterns current models handle badly (reasoning-in-response requests, redundant "double-check" instructions, hard-coded model IDs, removed parameters).

## Measuring it

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-dark.svg">
  <img src=".github/assets/benchmark.svg" alt="Routing benchmark on 52 held-out requests: description match 17%, random skill in the router's phases 50%, router without phase detection 33%, without role priors 54%, Open Skill router 67%, with 95% Wilson intervals" width="960">
</picture>

On the 52 held-out requests, the router passes 67% [54–78%] of cases, against 17% [9–30%] for picking the one skill whose description matches best (BM25 over the same index): 29 wins, 3 losses, exact McNemar p = 3×10⁻⁶. Removing phase detection drops it to 33%, removing role priors to 54%; a random skill in the router's own phases passes 50%. The 199 tuned cases all pass, as CI requires. A route takes a few milliseconds and 1,179 tests guard it. The labels are the maintainer's, 52 cases give wide intervals, and this measures routing, not the work that follows. `uv run python -m open_skill.benchmark` reproduces every number (`--json` for machine output); `scripts/render_assets.py` redraws the chart from it and CI checks it is current.

- `open-skill eval routing` runs the labeled routing cases (every role, frameworks, models) and reports pass rates per role, then the score on held-out cases the router was never tuned on (paraphrased, messy requests in English and Vietnamese, with and without accents). CI requires every tuned case to pass and the holdout to stay above a floor.
- `open-skill eval triggers` measures how well each core skill's description catches the requests it should and leaves near misses alone, using about 30 labeled queries per skill, of which the ones marked `holdout: true` are never used for tuning. By default it uses a deterministic lexical proxy (fast, runs in CI with regression floors) and lists misses and false alarms for the tuning queries only; `--agent claude --runs 3` runs every query through Claude Code, counts a trigger when the skill is invoked in at least half the runs, and reports precision and recall on the tuning and holdout queries, following the [description optimization guide](https://agentskills.io/skill-creation/optimizing-descriptions). `--suggest` adds, per skill, the words and phrases that missed tuning queries share but the description lacks, and the description words behind false alarms: hints at a missing concept, not words to paste in.

## Skill health

`open-skill lint` checks skills against the [Agent Skills specification](https://agentskills.io/specification) (name rules and folder match, field limits, referenced files) and against current prompting guidance; plugin manifests are checked too. Only errors fail; `--strict` fails on warnings and `--format json` feeds other tools. `open-skill lint --installed` gives a health report of every installed skill, grouped by source.

## Security audit

Skills run with your agent's permissions, so review one before you trust it. `open-skill audit` helps with that review: it reads every file in a skill folder (SKILL.md, references, scripts, assets) and reports lines worth a human look. It never runs, changes or follows links out of the files it audits.

```bash
open-skill audit ./downloaded-skill        # one folder before you install it
open-skill audit --installed               # everything installed, grouped by source
open-skill audit --installed --format json # for other tools
```

For code scanning, `--format sarif` writes a SARIF 2.1.0 log (`open-skill lint` has it too) with a `security-severity` per rule, so GitHub ranks the alerts; paths are relative to the current folder, so run it at the repository root (files outside it, such as `--installed` skills, become `file://` URIs that code scanning cannot place in the repository):

```yaml
# in a GitHub Actions job with `permissions: security-events: write`, after installing open-skill
- run: open-skill audit skills/ --format sarif > audit.sarif
# the audit exits 1 on a high finding; upload the log anyway
- uses: github/codeql-action/upload-sarif@v4
  if: always()
  with:
    sarif_file: audit.sarif
```

It flags text that tries to override the user's or system's instructions, hide actions from the user, skip or fake approval, impersonate the system or an administrator, or reach for SSH keys, cloud credentials, `.env` files, browser profiles and password stores; downloads piped straight into a shell, decoded text run as a command, known exfiltration endpoints and hard-coded tokens or private keys; writes to the agent's own instructions, memory or settings (`~/.claude/CLAUDE.md`, `.claude/settings.json`), which outlive the skill; invisible Unicode and HTML comments that address the agent; unscoped shell grants in `allowed-tools`, hooks a skill registers for the rest of the session and commands that run while a skill loads; links that leave the skill folder and bundled executables. Each finding shows the file, line, an escaped excerpt, why it matters and the public source of the rule (OWASP Top 10 for LLM and for Agentic Applications, MITRE ATT&CK, Anthropic and Claude Code documentation). The command exits 1 on high-severity findings; `--strict` also fails on medium and low. `open-skill doctor` shows a one-line summary.

This is a heuristic reviewer, not a guarantee. A finding can be harmless in context, and a clean report only means no rule matched: a careful attacker can phrase things the rules do not catch. Still read skills from unknown sources yourself, and prefer skills you or your organization maintain.

<img src=".github/assets/audit.svg" alt="Terminal: open-skill audit ./downloaded-skill reporting heuristic findings by severity with file and line" width="790">

## Learns you, locally

`~/.open-skill/` holds your profile, one-fact-per-file notes and a usage log. Routes attach the notes that apply to the chosen skills, roles, project or phases, and your history nudges rankings (with a 90-day half-life). `learn` refuses text that looks like a secret or personal data; `forget` and `export` are one command each; nothing in this folder is ever published. `open-skill scan --memory` imports Claude Code memory files read-only.

### Upgrading never touches your notes

Pulling a new release (plugin update, `npx skills update`, a new `uvx` version) replaces skills and the registry only; your data lives in `~/.open-skill/`, outside every skill folder. After pulling, run:

```bash
open-skill upgrade --dry-run   # see what would change
open-skill upgrade             # back up, migrate the data schema, sync starter knowledge
```

- Seeds you never edited follow the new wording; seeds you edited are kept, and the new wording waits in `seed-updates/` for `open-skill seeds diff | accept | keep`.
- Seeds you forgot are never re-created; seeds dropped upstream stay and are reported once.
- An older CLI refuses to write data created by a newer one. `open-skill upgrade --rollback`, `backup` and `restore` undo anything.

Organizations can add private skills and house rules as an **L1 overlay** (a separate repository with the same layout) via `--overlay` or `overlays:` in the profile, without forking this repository.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/safety-dark.svg">
  <img src=".github/assets/safety.svg" alt="User data safety: an upgrade backs up, migrates and syncs starter notes; unedited seeds are updated, edited seeds are kept with a proposal, dismissed seeds are never re-created, your own notes are never touched" width="960">
</picture>

<img src=".github/assets/upgrade.svg" alt="Terminal: open-skill upgrade --dry-run showing what an upgrade would do to notes from an older release" width="790">

## CLI

```text
open-skill route "<task>" [--project .] [--agent a] [--role r] [--size s] [--phase p] [--model m] [--explain | --why-not <skill>]
open-skill search ["<need>"] [--role r] [--phase p] [--source s] [--installed] [--agent a]
open-skill doctor                   open-skill scan [--agent a] [--memory]
open-skill agents [--project .]     open-skill install <skill|folder> --agent a [--project .] [--symlink] [--dry-run]
open-skill remove <skill> --agent a [--project .] [--dry-run]    open-skill update [--agent a] [--dry-run]
open-skill init --role r[=w]        open-skill learn "<fact>" --applies-to skill:<id>,role:<id>
open-skill feedback <route_id> --ran a,b --outcome ok|fail       open-skill forget <id>
open-skill validate | lint [paths] [--format json|sarif] | build [--check] | graph [--format mermaid|json|html] [--out file]
open-skill audit [paths] [--installed] [--format json|sarif] [--strict]
open-skill adapter draft|check --source <name> --from <upstream checkout>
open-skill session start --scope <glob> --task "..." | list [--prune] | end <id> | update [--session <id>] [--json]
```

Exit codes: 0 success, 1 a check failed (lint errors, a high audit finding, stale build, adapter drift, nothing to remove), 2 bad input (unknown role, phase, agent or path), 3 your data was written by a newer open-skill.

### JSON output

These outputs are for other tools; the keys listed are always present (more may be added, never removed in a minor release).

| Command | Shape | Keys |
|---|---|---|
| `open-skill route` | object | `route_id`, `task`, `agent`, `role`, `size`, `target_phase`, `phase_from`, `project`, `chain`, `advice`, `knowledge`, `missing`, `model` |
| `open-skill scan --json` | list of objects | `id`, `invoke`, `path`, `description`, `inferred`, `agent`, `agents` |
| `open-skill agents --json` | list of objects | `id`, `name`, `detected`, `skills`, `docs`, `install_to`, `reads` |
| `open-skill status --json` | object | `open_skill`, `registry`, `home`, `data_schema`, `cli_schema`, `pending_migrations`, `roles`, `notes`, `seed_updates_to_review`, `backups` |
| `open-skill lint --format json` | list of objects | `path`, `severity`, `rule`, `message`, `source` |
| `open-skill lint --installed --format json` | object per source | `skills`, `errors`, `warnings`, `worst` |
| `open-skill audit --format json` | object | `disclaimer`, `summary`, `groups` |
| `open-skill audit --format sarif` | object | `version`, `runs` (a SARIF 2.1.0 log with one run) |
| `open-skill lint --format sarif` | object | `version`, `runs` (a SARIF 2.1.0 log with one run) |
| `open-skill graph --format json` | object | `version`, `nodes`, `edges` |
| `open-skill eval routing --format json` | object | `cases`, `passed`, `pass_rate`, `by_role`, `results` |
| `open-skill eval triggers --format json` | object per skill | `train`, `validation` |

## Contributing

Add an adapter, a role pack or a model profile; see [CONTRIBUTING.md](CONTRIBUTING.md). Every change runs unit tests, routing evals for every role, schema validation, skill lint, a generated-files check and a privacy guard.

This repository is itself developed spec-driven: see `.specify/memory/constitution.md` and `specs/`.

## Acknowledgements

Built on ideas and work from superpowers (Jesse Vincent), BMad Method (BMad Code, LLC), spec-kit (GitHub), codegraph (Colby McHenry), Anthropic's Agent Skills and plugins, Context7 (Upstash), ponytail, taste-skill, Addy Osmani's agent-skills and Vercel's agent-skills. See [NOTICE](NOTICE).

## License

MIT © Võ Khôi Nhơn. Developed with Claude as co-author.
