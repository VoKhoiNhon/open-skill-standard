# Open Skill Standard

**One router, one skill graph, 28 IT roles.** An open, agent-agnostic standard for choosing the right Agent Skills for a task, and a reference implementation that ties together superpowers, BMad Method, spec-kit, codegraph, Anthropic's skills and more, without copying any of them.

[Tiếng Việt](README.vi.md) · [Specification](spec/SPEC.md) · [Contributing](CONTRIBUTING.md)

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
| Registry | 14 adapters describing 150+ upstream skills and tools, 28 role packs, 9 model profiles |

## Quick start

```bash
# 1. Install the skills (Claude Code) — or: npx skills add VoKhoiNhon/open-skill-standard -g
/plugin marketplace add VoKhoiNhon/open-skill-standard
/plugin install open-skill@open-skill-standard

# 2. Tell it your role(s); this also seeds starter knowledge for them
uvx --from git+https://github.com/VoKhoiNhon/open-skill-standard@v0.5.0 open-skill init --role data-engineer=0.7 --role data-analyst=0.3

# 3. In your agent, inside any project
/open-skill-router add a pipeline that loads orders into the warehouse
```

`open-skill doctor` shows which frameworks are installed and the official command for each one that is missing.

## How routing works

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

## Roles

| Family | Roles |
|---|---|
| Engineering | frontend-developer, backend-developer, fullstack-developer, mobile-developer, embedded-engineer, game-developer |
| Quality & operations | qa-engineer, devops-engineer, site-reliability-engineer, cloud-engineer, security-engineer, database-administrator, system-administrator |
| Data & AI | data-engineer, analytics-engineer, data-analyst, data-scientist, ml-engineer, ai-engineer, data-ai-platform-engineer |
| Architecture & leadership | software-architect, tech-lead, engineering-manager |
| Product & delivery | product-manager, business-analyst, ux-designer, technical-writer, scrum-master |

Each role pack states the role's characteristic risk, its principles, the project files that suggest it, and its primary and alternative skills per phase. Readable playbooks are generated into [`skills/open-skill-router/references/roles/`](skills/open-skill-router/references/roles/README.md).

## Integrated frameworks

Adapters describe upstream skills as metadata and point to the official installers; nothing is vendored.

| Source | Role in the chain | License |
|---|---|---|
| [superpowers](https://github.com/obra/superpowers) | Execution discipline: design approval, plans, TDD, debugging, verification | MIT |
| [BMad Method](https://github.com/bmad-code-org/BMAD-METHOD) | Thinking partners, personas, planning artifacts, right-sized build (needs `bmad setup`) | MIT, trademark |
| [spec-kit](https://github.com/github/spec-kit) | Durable spec → plan → tasks → implement → converge (needs `specify init`) | MIT |
| [codegraph](https://github.com/colbymchenry/codegraph) | Code knowledge graph: call paths, impact, affected tests | MIT |
| [Anthropic skills](https://github.com/anthropics/skills) | Documents, skill authoring, MCP servers, web testing, frontend design | per skill |
| [Knowledge-work plugins](https://github.com/anthropics/knowledge-work-plugins) | Data, engineering, product management, design | Apache-2.0 |
| [Context7](https://github.com/upstash/context7) | Current library documentation | MIT |
| [ponytail](https://github.com/DietrichGebert/ponytail) | Minimal solutions and over-engineering reviews | MIT |
| [taste-skill](https://github.com/leonxlnx/taste-skill) | Frontend visual quality | MIT |
| Claude Code built-ins | code-review, security-review, run, claude-api, schedule… | — |

## Adapts to the model

Prompting advice changes between model generations; instructions that helped one model can hurt the next. Skills here stay model-neutral, and model-specific notes live in [`registry/models/`](registry/models/): effort per task size, chain length, short prompting notes and patterns to avoid, each with its source in Anthropic's prompting guides. An unknown future model falls back to its family, then to `generic`, so nothing breaks; a weekly workflow opens an issue when the guides list a model without a profile. `open-skill lint` rejects patterns current models handle badly (reasoning-in-response requests, redundant "double-check" instructions, hard-coded model IDs, removed parameters).

## Measuring it

- `open-skill eval routing` runs the labeled routing cases (every role, frameworks, models) and reports pass rates per role.
- `open-skill eval triggers` measures how well each core skill's description catches the requests it should and leaves near misses alone, using about 30 labeled queries per skill, of which the ones marked `holdout: true` are never used for tuning. By default it uses a deterministic lexical proxy (fast, runs in CI with regression floors) and lists misses and false alarms for the tuning queries only; `--agent claude --runs 3` runs every query through Claude Code, counts a trigger when the skill is invoked in at least half the runs, and reports precision and recall on the tuning and holdout queries, following the [description optimization guide](https://agentskills.io/skill-creation/optimizing-descriptions).

## Skill health

`open-skill lint` checks skills against the [Agent Skills specification](https://agentskills.io/specification) (name rules and folder match, field limits, referenced files) and against current prompting guidance; plugin manifests are checked too. Only errors fail; `--strict` fails on warnings and `--format json` feeds other tools. `open-skill lint --installed` gives a health report of every installed skill, grouped by source.

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

## CLI

```text
open-skill route "<task>" [--project .] [--role r] [--size s] [--model m] [--explain]
open-skill search "<need>"          open-skill doctor           open-skill scan [--memory]
open-skill init --role r[=w]        open-skill learn "<fact>" --applies-to skill:<id>,role:<id>
open-skill feedback <route_id> --ran a,b --outcome ok|fail       open-skill forget <id>
open-skill validate | lint [paths] | build [--check] | graph [--format json]
open-skill adapter draft|check --source <name> --from <upstream checkout>
```

## Contributing

Add an adapter, a role pack or a model profile; see [CONTRIBUTING.md](CONTRIBUTING.md). Every change runs unit tests, routing evals for every role, schema validation, skill lint, a generated-files check and a privacy guard.

This repository is itself developed spec-driven: see `.specify/memory/constitution.md` and `specs/`.

## Acknowledgements

Built on ideas and work from superpowers (Jesse Vincent), BMad Method (BMad Code, LLC), spec-kit (GitHub), codegraph (Colby McHenry), Anthropic's Agent Skills and plugins, Context7 (Upstash), ponytail and taste-skill. See [NOTICE](NOTICE).

## License

MIT © Võ Khôi Nhơn. Developed with Claude as co-author.
