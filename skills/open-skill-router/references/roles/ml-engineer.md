<!-- Generated from registry/roles/ml-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# ML Engineer / MLOps playbook

Takes models to production: training pipelines, feature stores, serving and monitoring.

**Characteristic risk:** Models that degrade silently after deployment through drift or training/serving skew.

## Principles

- Training is reproducible: data version, seed and config are recorded.
- Offline and online features are computed the same way.
- Production models are monitored for drift and performance.
- Every release has a model card.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `knowledge-work-engineering/system-design` — Design systems, services and architectures<br>`superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan | `spec-kit/plan` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `knowledge-work-data/statistical-analysis` — Descriptive statistics, trends, outliers and hypothesis tests<br>`knowledge-work-data/validate-data` — QA an analysis or dataset before sharing - methodology, accuracy, bias | `superpowers/verification-before-completion` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`superpowers/requesting-code-review` — Ask for a review of finished work before merging | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review`<br>`knowledge-work-engineering/code-review` |
| release | `knowledge-work-engineering/deploy-checklist` — Pre-deployment verification for releases, migrations and flags | `superpowers/finishing-a-development-branch` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/incident-response`<br>`claude-code-builtin/schedule` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Log the feature values used at prediction time.
- Shadow a new model before it serves traffic.
- Alert on input drift, not only on accuracy.

## Project signals

`**/train*.py`, `mlflow*`, `dvc.yaml`, `**/feature_store/**`, `bentofile.yaml`, `**/serving/**`
