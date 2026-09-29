<!-- Generated from registry/roles/data-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Data Engineer playbook

Builds and runs pipelines that move, model and serve data reliably.

**Characteristic risk:** Silently wrong numbers: pipelines succeed while the data is wrong.

## Principles

- Loads are idempotent: re-running a date range never duplicates data.
- Every run is reconciled against its source (row counts, key totals).
- Schema changes are declared and downstream consumers are checked.
- No personal data in logs, repositories or prompts.
- Shared tables have a data contract (ODCS).

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `bmad-method/bmad-deep-recon`<br>`knowledge-work-data/explore-data` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec<br>`spec-kit/tasks` — Generate a dependency-ordered tasks.md from the plan | `bmad-method/bmad-architecture`<br>`knowledge-work-engineering/architecture` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`knowledge-work-data/sql-queries` |
| verify | `knowledge-work-data/validate-data` — QA an analysis or dataset before sharing - methodology, accuracy, bias<br>`knowledge-work-data/explore-data` — Profile a dataset - shape, nulls, distributions, duplicates, quality issues<br>`open-skill/open-skill-standards` — Definition-of-done checklists, general and per role | `superpowers/verification-before-completion` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`codegraph/impact` — Blast radius of changing a symbol (codegraph impact)<br>`ponytail/ponytail-review` — Review a diff only for over-engineering and what to delete | `bmad-method/bmad-code-review`<br>`knowledge-work-data/sql-queries` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `claude-code-builtin/schedule`<br>`knowledge-work-engineering/incident-response` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them<br>`bmad-method/bmad-retrospective` — Evidence-based retrospective of a finished epic | — |

## Starter knowledge

- Use MERGE on the business key instead of a blind INSERT.
- Check nulls and duplicates on primary and business keys after every load.
- Backfill in bounded batches and verify each batch before the next.
- Filter on the partition column; never scan a large table without it.
- When a number disagrees with the dashboard, fix the rule that generated the query, not the single query.
- codegraph does not index SQL; search dbt and SQL repositories by table name.

## Project signals

`dbt_project.yml`, `**/dags/**`, `databricks.yml`, `**/pipelines/**`, `**/*.sql`, `**/spark/**`

## Hand-offs

- reporting → `data-analyst` playbook
- modeling → `data-scientist` playbook
