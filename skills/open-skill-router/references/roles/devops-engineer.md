<!-- Generated from registry/roles/devops-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# DevOps Engineer playbook

Builds and runs CI/CD, environments and developer tooling.

**Characteristic risk:** A pipeline or infrastructure change that breaks every team's deploys.

## Principles

- Everything is code and changes through pull requests.
- Every change has a tested rollback path.
- Secrets live in a secret manager, never in code or CI logs.
- Pipelines are fast, cached and reproducible.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`knowledge-work-engineering/architecture` — Create or evaluate an architecture decision record | `spec-kit/plan` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md | `bmad-method/bmad-build`<br>`ponytail/ponytail` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `claude-code-builtin/security-review` — Security review of pending changes<br>`claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`codegraph/impact` — Blast radius of changing a symbol (codegraph impact) | `ponytail/ponytail-review` |
| release | `knowledge-work-engineering/deploy-checklist` — Pre-deployment verification for releases, migrations and flags<br>`superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | — |
| operate | `knowledge-work-engineering/incident-response` — Triage, communicate and write the postmortem for an incident<br>`superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `claude-code-builtin/update-config` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Pin action and image versions; float nothing in CI.
- Keep deploy and rollback as the same command with a different version.
- Fail the pipeline on a secret found in the diff.

## Project signals

`.github/workflows/**`, `.gitlab-ci.yml`, `Jenkinsfile`, `Dockerfile`, `**/*.tf`, `helm/**`, `k8s/**`
