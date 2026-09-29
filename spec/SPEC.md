# Open Skill Standard — Specification v0.1

**Status:** Draft · **Date:** 2026-09-29 · **License:** MIT

The key words MUST, SHOULD and MAY are used as described in RFC 2119.

## 1. Scope

This standard describes Agent Skills (folders containing a `SKILL.md`) by the roles they serve, the lifecycle phases they act in, and the artifacts they consume and produce, so that an agent can select and order skills deterministically, explain the choice, and adapt it to the user and the model. It does not change the `SKILL.md` format itself; it adds metadata alongside it.

## 2. Terms

- **Skill** — an Agent Skill an agent can invoke by name.
- **Tool** — an MCP server or CLI a skill chain can use (for example, a code graph).
- **Agent target** — a registry document naming one coding agent and the folders it loads skills from.
- **Adapter** — a registry document that describes the skills of one upstream source as metadata, without copying their content.
- **Role pack** — a registry document describing one IT role: its characteristic risk, principles, project signals, phase-to-skill mapping and starter knowledge.
- **Model profile** — a registry document with prompting notes and limits for one model or model family.
- **Knowledge node** — one user-specific fact (lesson, preference, glossary term, project fact, pitfall).
- **Route** — an ordered chain of skills chosen for one task.

## 3. Taxonomy

`spec/taxonomy.yaml` is normative. It defines:

- **Phases**, in order: discover, research, specify, plan, build, verify, review, release, operate, learn. Each phase has English keywords, and MAY have keywords in other languages (§3.1), used to detect a task's target phase. Keywords match whole words and phrases, ignoring case and hyphens; a task typed without diacritics matches them folded the way the search index folds text (so `cafe` matches `café`), while a task typed with diacritics keeps them (`papá` does not match `papa`). A keyword written in a script without spaces between words (Japanese, Chinese, Thai) matches anywhere in the task. A phase MAY also list `generic` keywords, which count as hits but do not break ties, and `symptoms`, which break ties against build and release; both take `_i18n` blocks like `keywords`.
- **Artifacts** (19 types) and the repository globs that reveal them.
- **Edge types:** produces, consumes, precedes, alternative-to, conflicts-with, requires, applies-to, recommends.
- **Task sizes:** small, medium, large, with keywords that hint at size.
- **Role families** and the 28 role identifiers.
- **Native markers:** project paths that make a framework own the build workflow (`.specify` → spec-kit, `_bmad` → BMad Method), in precedence order.
- **Knowledge types.**

Implementations MUST reject documents whose phases, artifacts, roles or sizes are not in the taxonomy.

### 3.1 Locales

English is the canonical language of the standard. A list of words that people type — phase `keywords`, `size_keywords`, `stopwords` (words search ignores) and adapter `triggers` — holds English only. Words in another language go in a block beside it named `<field>_i18n`, keyed by a BCP 47 language tag and holding what the field holds:

```yaml
phases:
  - id: operate
    keywords: [incident, error, "not working"]
    keywords_i18n:
      vi: [sự cố, lỗi, "không chạy"]
      es: [incidente, "no funciona"]
size_keywords:
  small: [typo, rename]
size_keywords_i18n:
  es:
    small: [errata, renombrar]
skills:
  - name: systematic-debugging
    triggers: [bug, debug, "root cause"]
    triggers_i18n: {es: [depurar, "causa raíz"]}
```

`en` and its subtags are not valid block keys. Implementations MUST treat a field as its English list plus every block, so a new language needs only new blocks: no code change, no change to the English lists. The generated schemas reject a misspelled block name or a malformed tag. Search matches whole words, so for languages written without spaces between words, triggers help less than keywords do. To add a language, add its blocks, then add routing cases in that language to `evals/routing.yaml` and the holdout, and trigger queries with `locale: <tag>` to `evals/triggers/`. Skill descriptions stay English; agents read them, and the registry's blocks carry the other languages.

## 4. Documents

JSON Schemas generated from the taxonomy live in `spec/schemas/` and are normative for document structure.

### 4.1 Adapter (`registry/adapters/<source>.yaml`)

An adapter MUST contain `source`, `upstream`, `license` and `skills`. It SHOULD contain `install` (commands copied verbatim from the upstream README) and `detect` rules. An `install` key MAY end in `@<agent id>` for that agent's variant of the command; once a key has variants, the plain key is for Claude Code and an agent with no variant has none. It MUST NOT contain upstream skill bodies.

Each skill entry MUST have `name` (the folder name agents invoke) and `phases`, and MAY have `description` (a short summary in the adapter author's own words, in English), `kind` (skill, tool, or meta for a router, session bootstrap or metadata record, which a router MUST NOT place in a route), `roles` (weights 0–1), `produces`, `consumes`, `alternatives`, `conflicts`, `precedes`, `requires`, `task_size`, `triggers` (English), `triggers_i18n` (§3.1), `portability`, `installed_as`.

Skill identifiers are `<source>/<name>`.

`requires` entries take the forms `tool:<name>`, `skill:<id>`, or `project:<relative path>`. A skill whose `project:` requirement is not met MUST NOT be placed in a route; it MAY be reported as missing with an install hint.

`available_env` names an environment variable whose presence makes every skill of the adapter count as installed (for skills built into an agent). `available_cmd` names a command whose presence on `PATH` makes every skill of the adapter count as installed for every agent (for tools such as a code graph CLI); a skill's `invoke` then says how to call it.

### 4.2 Detect rules

A detect rule is `{glob, invoke}` and MAY name the `agent` (an agent target id, §4.6) whose folders it describes; the default is `claude-code`. The glob MAY contain `~` (home), `{project}` (project root) and `{name}` (one path segment, the skill name). It MAY start with `{skills}` (every user-level skill folder of every agent target) or `{project_skills}` (every project skill folder of every agent target, under the project root); such a rule applies to each folder for the agents that read it. `invoke` is a template producing the name the agent calls. Rules are evaluated in order; the first rule that finds a skill wins its path and, for each agent, its invocation name. A rule whose `{name}` segment has no source-specific prefix or path component MUST only claim names listed in the adapter. A rule MAY list `names`; it then claims only those names, for plugins whose folders hold more skills than they expose. A folder matching a skill's `installed_as` (the name an installer gives the folder when it differs from `name`) is that skill, and `invoke` is built from the folder name.

An implementation MUST report a skill that several agents see once, with the name each agent invokes it by. A folder that several agents read belongs first to the agent that lists it first. Relocation variables (§4.6) apply to the folders of their agent.

### 4.3 Role pack (`registry/roles/<role-id>.yaml`)

A role pack MUST contain `id`, `name`, `family`, `summary`, `risk`, `constitution` (at least three principles) and `phases`. Each phase entry lists `primary` skill ids and MAY list `alternatives`. A role pack MAY define `build_window`, the phases a build-type task walks through for that role, and `seeds`, generic starter knowledge. Role packs MUST NOT contain organization-specific names or data.

### 4.4 Model profile (`registry/models/<id>.yaml`)

A model profile MUST contain `id`, `match` (globs), `source` and `verified` (a date, or `false` when unmeasured). It MAY contain `family`, `inherits`, `traits`, `effort` (per task size), `chain.max_steps`, `addenda` (short prompting notes) and `avoid` (patterns to keep out of prompts). A profile named `generic` MUST exist and match any model.

### 4.5 Knowledge node

Knowledge nodes are Markdown files with frontmatter `id`, `type`, `applies_to` (entries `skill:`, `role:`, `project:`, `phase:`, with `role:*` meaning all), `source` (user, seed, agent-memory, org) and `created`.

### 4.6 Agent target (`registry/agents/<id>.yaml`)

An agent target describes one coding agent that loads Agent Skills. It MUST contain `id`, `name`, `docs`, `global` (user-level skill folders) and `detect` (paths whose existence shows the agent is installed), and MAY contain `project` (skill folders relative to the project root), `relocate` and `notes`. The first folder of `global` and of `project` is where skills are installed for that agent; the others are folders it also reads.

Every path entry MUST carry a `source`: the URL of the official documentation, or of the upstream source line, that states the path. `global` and `detect` paths start with `~/` or `/`; `project` paths are relative and MUST NOT leave the project. A `relocate` entry `{var, replaces, source}` means that when the environment variable `var` is set and not empty, its value replaces the path prefix `replaces` (for example `CODEX_HOME` for `~/.codex`).

## 5. Layers

Documents are merged in order: **L0** public registry, **L1** organization overlays, **L2** the user's local layer. Later layers override earlier ones by identifier. L2 data (profile, knowledge, usage events) MUST stay on the user's machine and MUST NOT be published with L0.

### 5.1 Upgrade guarantees

A conforming implementation:

1. MUST record a schema version for the user layer and MUST refuse to write data whose version is newer than it understands.
2. MUST back up the user layer before migrating it, and MUST keep the text of user notes unchanged during migration.
3. MUST NOT overwrite a seed note the user edited; it SHOULD record the hash of each seed as installed to detect edits, and SHOULD offer upstream's new wording for review instead.
4. MUST NOT re-create a seed the user deleted, and MUST NOT delete a seed only because upstream stopped shipping it.
5. SHOULD offer a dry run and a rollback for every upgrade.

### 5.2 Installing skills into agents

A conforming implementation that installs skills into an agent's folders (§4.6):

1. MUST NOT overwrite, change or delete a skill folder it did not create. It MAY leave an identical existing skill in place, but MUST NOT then record it as created.
2. MUST record in the user layer every folder it creates, with a content hash of each file it wrote and the version that wrote it.
3. When removing, MUST delete only recorded files whose content still matches, MUST NOT reach files through links, and MUST keep files the user changed or added. A link it created MAY be removed only while it still points at the recorded source.
4. When updating, MUST skip any install the user changed, and SHOULD swap the new copy in so that a failure leaves the old one.
5. MUST reject skill names that are not valid Agent Skills names, so every install stays inside the agent's folder, and SHOULD offer a dry run.

## 6. Routing

A conforming router, given a task, a project and optionally a role, size and model:

1. MUST inspect the project for native markers, artifacts and role signals without reading file contents.
2. MUST resolve a role mix from, in order, the explicit role, the user's profile, project signals.
3. MUST choose a target phase and a phase window, and SHOULD use a role pack's `build_window` for build-type tasks. A phase given by the caller MUST be a taxonomy phase id and MUST be used as is; otherwise the router MAY detect it from phase keywords. It MUST report where the phase came from (given, keywords, or guessed when nothing matched).
4. MUST only place installed skills whose requirements are met; MUST NOT place two skills that conflict; MUST let the project's native framework win the phases it has candidates for.
5. SHOULD rank candidates by role pack membership, role weights, text relevance, artifact flow and the user's personal weights, and MUST be able to explain each choice. A missing role prior SHOULD NOT hold back a strong text match. The reference router scores `fit = max(prior × (1 + 3s/(s+4)), s/6)`, where `s` is the skill's BM25 relevance to the task and `prior` is 2.0 for a role pack primary, 0.7 for an alternative, otherwise the manifest's weight for the role (0.2 when it names other roles, 0.3 when it names none, 0.5 for a skill without a manifest), then multiplies by the user's personal weight, 0.8 for skills without a manifest and 1.25 when the skill consumes an artifact available at that step. The first term lets the role lead while text only saturates (at most 4×); the second lets text alone carry a skill, so a match of BM25 12, the top tenth of best matches, ties a primary with no text match.
6. MUST resolve a model profile, falling back from exact match to family to `generic`, and apply its step limit and notes. Matching ignores case, a context suffix such as `[1m]` and a provider prefix such as `us.anthropic.` or `anthropic/`.
7. SHOULD attach applicable knowledge nodes and report missing skills with install hints; MUST NOT run project initialization commands on the user's behalf.
8. SHOULD record proposed routes and the skills that actually ran, locally, to learn personal weights.

## 7. Skill writing rules

Skills published under this standard MUST conform to the [Agent Skills specification](https://agentskills.io/specification) and MUST pass `open-skill lint` without errors: `name` of 1–64 lowercase letters, digits and single hyphens, not starting or ending with a hyphen, matching its folder, without "claude" or "anthropic"; `description` of 1–1024 characters without angle brackets; `compatibility` of 1–500 characters when present; `metadata` mapping strings to strings; every referenced file present. They SHOULD keep `SKILL.md` under 500 lines and about 5000 tokens, and SHOULD avoid fields no agent reads. They MUST NOT ask the model to reproduce its reasoning in the response or use removed API parameters. They SHOULD avoid redundant self-verification instructions, hard-coded model identifiers and pervasive capitalized MUST/NEVER. Model-specific guidance belongs in model profiles, not skills.

## 8. Versioning

The standard uses semantic versioning. Adding taxonomy values is a minor change; removing or renaming them is a major change.
