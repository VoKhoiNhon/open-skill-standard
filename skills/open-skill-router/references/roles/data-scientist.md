<!-- Generated from registry/roles/data-scientist.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Data Scientist playbook

Frames questions as hypotheses and answers them with statistics and models.

**Characteristic risk:** Answering the wrong question, or leakage that makes a model look better than it is.

## Principles

- A simple baseline comes first.
- Splits respect time when the data has time.
- Uncertainty is reported with every estimate.
- Seed, data snapshot and parameters are recorded.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-brainstorming` |
| research | `bmad-method/bmad-deep-recon` — Decision research - market, domain, technical, competitive, academic, with cited sources<br>`knowledge-work-data/explore-data` — Profile a dataset - shape, nulls, distributions, duplicates, quality issues | `open-skill/open-skill-intel` |
| specify | `bmad-method/bmad-spec` — Condense ideas, briefs or transcripts into a short kernel spec<br>`spec-kit/specify` — Write the feature specification - what and why, not how | — |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec<br>`spec-kit/tasks` — Generate a dependency-ordered tasks.md from the plan | `bmad-method/bmad-ticket`<br>`knowledge-work-engineering/system-design` |
| build | `knowledge-work-data/statistical-analysis` — Descriptive statistics, trends, outliers and hypothesis tests<br>`knowledge-work-data/explore-data` — Profile a dataset - shape, nulls, distributions, duplicates, quality issues<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `knowledge-work-data/analyze` |
| verify | `knowledge-work-data/validate-data` — QA an analysis or dataset before sharing - methodology, accuracy, bias<br>`bmad-method/bmad-advanced-elicitation` — Make the model critique and refine its own output - pre-mortem, red team, socratic, first principles | `bmad-method/bmad-party-mode` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`superpowers/requesting-code-review` — Ask for a review of finished work before merging | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review`<br>`knowledge-work-engineering/code-review` |
| release | `knowledge-work-data/create-viz` — Publication-quality charts with Python<br>`knowledge-work-data/build-dashboard` — Interactive HTML dashboard with KPI cards, charts and filters | `anthropic-skills/pptx`<br>`anthropic-skills/docx` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Features may only use information available before the prediction time.
- Always compare against a naive model.
- Record the seed and the data snapshot with every result.

## Project signals

`**/*.ipynb`, `**/notebooks/**`, `**/experiments/**`, `requirements.txt`

## Hand-offs

- production pipeline → `data-engineer` playbook
- model serving → `ml-engineer` playbook
