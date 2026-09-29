<!-- Generated from registry/roles/database-administrator.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Database Administrator playbook

Keeps databases correct, fast, backed up and secure.

**Characteristic risk:** Locking, data loss or slow queries caused by schema changes.

## Principles

- Migrations are rehearsed on a production-sized copy.
- Backups are restored in drills, not only taken.
- Index and query changes are measured before and after.
- Access uses least-privilege roles.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec<br>`spec-kit/tasks` — Generate a dependency-ordered tasks.md from the plan | `bmad-method/bmad-ticket`<br>`knowledge-work-engineering/system-design`<br>`addy-agent-skills/deprecation-and-migration` |
| build | `knowledge-work-data/sql-queries` — Correct, performant SQL across warehouse dialects; optimize and translate<br>`knowledge-work-data/write-query` — Translate a data need into optimized SQL for your dialect | `superpowers/test-driven-development` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `knowledge-work-data/sql-queries` — Correct, performant SQL across warehouse dialects; optimize and translate<br>`claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs | `bmad-method/bmad-review` |
| release | `knowledge-work-engineering/deploy-checklist` — Pre-deployment verification for releases, migrations and flags | — |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/incident-response` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Add columns as nullable first, backfill, then add the constraint.
- Check the query plan before and after an index change.
- Test a restore every quarter.

## Project signals

`**/migrations/**`, `**/*.sql`, `schema.prisma`, `liquibase*`, `flyway*`
