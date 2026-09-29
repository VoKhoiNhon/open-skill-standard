<!-- Generated from registry/roles/analytics-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Analytics Engineer playbook

Models warehouse data into tested, documented, reusable datasets and metrics.

**Characteristic risk:** Metric definitions that drift between models and dashboards.

## Principles

- Each metric has exactly one definition, in the semantic layer.
- Every model has tests: unique, not null, relationships, accepted values.
- Models are documented where they are defined.
- Changed models are reconciled against the previous version.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec<br>`spec-kit/tasks` — Generate a dependency-ordered tasks.md from the plan | `bmad-method/bmad-ticket`<br>`knowledge-work-engineering/system-design` |
| build | `knowledge-work-data/sql-queries` — Correct, performant SQL across warehouse dialects; optimize and translate<br>`knowledge-work-data/write-query` — Translate a data need into optimized SQL for your dialect<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `superpowers/subagent-driven-development`<br>`spec-kit/implement`<br>`bmad-method/bmad-build` |
| verify | `knowledge-work-data/validate-data` — QA an analysis or dataset before sharing - methodology, accuracy, bias<br>`knowledge-work-data/explore-data` — Profile a dataset - shape, nulls, distributions, duplicates, quality issues | `open-skill/open-skill-standards` |
| review | `knowledge-work-data/sql-queries` — Correct, performant SQL across warehouse dialects; optimize and translate<br>`claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs | `ponytail/ponytail-review` |
| release | `knowledge-work-data/build-dashboard` — Interactive HTML dashboard with KPI cards, charts and filters | `knowledge-work-data/create-viz` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `knowledge-work-data/data-context-extractor` — Build a company-specific data knowledge skill from analysts' tribal knowledge<br>`open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | — |

## Starter knowledge

- Define the grain of every model in its first line of documentation.
- Compare row counts and key metrics between the old and new model before merging.
- Never compute the same metric in two places.

## Project signals

`dbt_project.yml`, `models/**/*.sql`, `**/semantic_models/**`, `**/*.lkml`, `**/metrics/*.yml`
