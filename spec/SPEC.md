# Open Skill Standard — Specification v0.1

**Status:** Draft · **Date:** 2026-09-29 · **License:** MIT

The key words MUST, SHOULD and MAY are used as described in RFC 2119.

## 1. Scope

This standard describes Agent Skills (folders containing a `SKILL.md`) by the roles they serve, the lifecycle phases they act in, and the artifacts they consume and produce, so that an agent can select and order skills deterministically, explain the choice, and adapt it to the user and the model. It does not change the `SKILL.md` format itself; it adds metadata alongside it.

## 2. Terms

- **Skill** — an Agent Skill an agent can invoke by name.
- **Tool** — an MCP server or CLI a skill chain can use (for example, a code graph).
- **Adapter** — a registry document that describes the skills of one upstream source as metadata, without copying their content.
- **Role pack** — a registry document describing one IT role: its characteristic risk, principles, project signals, phase-to-skill mapping and starter knowledge.
- **Model profile** — a registry document with prompting notes and limits for one model or model family.
- **Knowledge node** — one user-specific fact (lesson, preference, glossary term, project fact, pitfall).
- **Route** — an ordered chain of skills chosen for one task.

## 3. Taxonomy

`spec/taxonomy.yaml` is normative. It defines:

- **Phases**, in order: discover, research, specify, plan, build, verify, review, release, operate, learn. Each phase has keywords (any language) used to detect a task's target phase.
- **Artifacts** (19 types) and the repository globs that reveal them.
- **Edge types:** produces, consumes, precedes, alternative-to, conflicts-with, requires, applies-to, recommends.
- **Task sizes:** small, medium, large, with keywords that hint at size.
- **Role families** and the 28 role identifiers.
- **Native markers:** project paths that make a framework own the build workflow (`.specify` → spec-kit, `_bmad` → BMad Method), in precedence order.
- **Knowledge types.**

Implementations MUST reject documents whose phases, artifacts, roles or sizes are not in the taxonomy.

## 4. Documents

JSON Schemas generated from the taxonomy live in `spec/schemas/` and are normative for document structure.

### 4.1 Adapter (`registry/adapters/<source>.yaml`)

An adapter MUST contain `source`, `upstream`, `license` and `skills`. It SHOULD contain `install` (commands copied verbatim from the upstream README) and `detect` rules. It MUST NOT contain upstream skill bodies.

Each skill entry MUST have `name` (the folder name agents invoke) and `phases`, and MAY have `description` (a short summary in the adapter author's own words), `kind` (skill or tool), `roles` (weights 0–1), `produces`, `consumes`, `alternatives`, `conflicts`, `precedes`, `requires`, `task_size`, `triggers`, `portability`.

Skill identifiers are `<source>/<name>`.

`requires` entries take the forms `tool:<name>`, `skill:<id>`, or `project:<relative path>`. A skill whose `project:` requirement is not met MUST NOT be placed in a route; it MAY be reported as missing with an install hint.

`available_env` names an environment variable whose presence makes every skill of the adapter count as installed (for skills built into an agent).

### 4.2 Detect rules

A detect rule is `{glob, invoke}`. The glob MAY contain `~` (home), `{project}` (project root) and `{name}` (one path segment, the skill name). `invoke` is a template producing the name the agent calls. Rules are evaluated in order; the first rule that finds a skill wins. A rule whose `{name}` segment has no source-specific prefix or path component MUST only claim names listed in the adapter.

### 4.3 Role pack (`registry/roles/<role-id>.yaml`)

A role pack MUST contain `id`, `name`, `family`, `summary`, `risk`, `constitution` (at least three principles) and `phases`. Each phase entry lists `primary` skill ids and MAY list `alternatives`. A role pack MAY define `build_window`, the phases a build-type task walks through for that role, and `seeds`, generic starter knowledge. Role packs MUST NOT contain organization-specific names or data.

### 4.4 Model profile (`registry/models/<id>.yaml`)

A model profile MUST contain `id`, `match` (globs), `source` and `verified` (a date, or `false` when unmeasured). It MAY contain `family`, `inherits`, `traits`, `effort` (per task size), `chain.max_steps`, `addenda` (short prompting notes) and `avoid` (patterns to keep out of prompts). A profile named `generic` MUST exist and match any model.

### 4.5 Knowledge node

Knowledge nodes are Markdown files with frontmatter `id`, `type`, `applies_to` (entries `skill:`, `role:`, `project:`, `phase:`, with `role:*` meaning all), `source` (user, seed, agent-memory, org) and `created`.

## 5. Layers

Documents are merged in order: **L0** public registry, **L1** organization overlays, **L2** the user's local layer. Later layers override earlier ones by identifier. L2 data (profile, knowledge, usage events) MUST stay on the user's machine and MUST NOT be published with L0.

### 5.1 Upgrade guarantees

A conforming implementation:

1. MUST record a schema version for the user layer and MUST refuse to write data whose version is newer than it understands.
2. MUST back up the user layer before migrating it, and MUST keep the text of user notes unchanged during migration.
3. MUST NOT overwrite a seed note the user edited; it SHOULD record the hash of each seed as installed to detect edits, and SHOULD offer upstream's new wording for review instead.
4. MUST NOT re-create a seed the user deleted, and MUST NOT delete a seed only because upstream stopped shipping it.
5. SHOULD offer a dry run and a rollback for every upgrade.

## 6. Routing

A conforming router, given a task, a project and optionally a role, size and model:

1. MUST inspect the project for native markers, artifacts and role signals without reading file contents.
2. MUST resolve a role mix from, in order, the explicit role, the user's profile, project signals.
3. MUST choose a target phase and a phase window, and SHOULD use a role pack's `build_window` for build-type tasks.
4. MUST only place installed skills whose requirements are met; MUST NOT place two skills that conflict; MUST let the project's native framework win the phases it has candidates for.
5. SHOULD rank candidates by role pack membership, role weights, text relevance, artifact flow and the user's personal weights, and MUST be able to explain each choice.
6. MUST resolve a model profile, falling back from exact match to family to `generic`, and apply its step limit and notes.
7. SHOULD attach applicable knowledge nodes and report missing skills with install hints; MUST NOT run project initialization commands on the user's behalf.
8. SHOULD record proposed routes and the skills that actually ran, locally, to learn personal weights.

## 7. Skill writing rules

Skills published under this standard MUST pass `open-skill lint`: name kebab-case ≤ 64 characters without "claude" or "anthropic"; description ≤ 1024 characters without angle brackets; `SKILL.md` under 500 lines; no instructions to reproduce reasoning in the response; no redundant self-verification instructions; no hard-coded model identifiers; no removed API parameters; no pervasive capitalized MUST/NEVER. Model-specific guidance belongs in model profiles, not skills.

## 8. Versioning

The standard uses semantic versioning. Adding taxonomy values is a minor change; removing or renaming them is a major change.
