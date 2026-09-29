<!-- Generated from registry/roles/data-analyst.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Data Analyst playbook

Answers business questions with data and communicates what the numbers mean.

**Characteristic risk:** Decisions ride on the numbers: a wrong denominator becomes a wrong decision.

## Principles

- Every number states its source table, layer and time range.
- Metric definitions are explicit, including the denominator.
- Analyses are QA'd before they are sent.
- No personal identifiers in reports.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped<br>`knowledge-work-product-management/product-brainstorming` — Explore problem spaces and challenge assumptions as a thinking partner | — |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting | `knowledge-work-data/explore-data` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec<br>`spec-kit/tasks` — Generate a dependency-ordered tasks.md from the plan | `bmad-method/bmad-ticket`<br>`knowledge-work-engineering/system-design` |
| build | `knowledge-work-data/analyze` — Answer data questions from quick lookups to full analyses<br>`knowledge-work-data/write-query` — Translate a data need into optimized SQL for your dialect | `knowledge-work-data/sql-queries`<br>`anthropic-skills/xlsx` |
| verify | `knowledge-work-data/validate-data` — QA an analysis or dataset before sharing - methodology, accuracy, bias<br>`bmad-method/bmad-advanced-elicitation` — Make the model critique and refine its own output - pre-mortem, red team, socratic, first principles | `knowledge-work-data/statistical-analysis` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`superpowers/requesting-code-review` — Ask for a review of finished work before merging | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review`<br>`knowledge-work-engineering/code-review` |
| release | `knowledge-work-data/create-viz` — Publication-quality charts with Python<br>`knowledge-work-data/build-dashboard` — Interactive HTML dashboard with KPI cards, charts and filters | `anthropic-skills/pptx`<br>`anthropic-skills/xlsx`<br>`anthropic-skills/docx` |
| operate | `claude-code-builtin/schedule` — Scheduled cloud agents on a cron | — |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Write down the denominator of every rate.
- Bar charts start at zero.
- Compare with the official dashboard and state the difference.

## Project signals

`**/*.sql`, `**/*.ipynb`, `**/reports/**`, `**/dashboards/**`
