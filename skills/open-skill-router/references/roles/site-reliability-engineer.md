<!-- Generated from registry/roles/site-reliability-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Site Reliability Engineer playbook

Keeps services reliable with SLOs, alerting, incident response and automation of toil.

**Characteristic risk:** Unreliable service, or noisy alerts that hide the real incident.

## Principles

- Services have SLOs with error budgets that guide release pace.
- Every alert is actionable and links to a runbook.
- Postmortems are blameless and end with owned actions.
- Repeated manual work gets automated.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `codegraph/explore` — Answer how code works, trace flows and read symbols with call paths (MCP codegraph_explore)<br>`open-skill/open-skill-intel` — Route a question to the best information source before acting | `context7/context7-mcp` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `knowledge-work-engineering/system-design` — Design systems, services and architectures<br>`superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan | `knowledge-work-engineering/architecture` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`superpowers/requesting-code-review` — Ask for a review of finished work before merging | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review`<br>`knowledge-work-engineering/code-review` |
| release | `knowledge-work-engineering/deploy-checklist` — Pre-deployment verification for releases, migrations and flags | `superpowers/finishing-a-development-branch` |
| operate | `knowledge-work-engineering/incident-response` — Triage, communicate and write the postmortem for an incident<br>`superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`claude-code-builtin/schedule` |
| learn | `knowledge-work-engineering/incident-response` — Triage, communicate and write the postmortem for an incident<br>`open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Write the runbook link into the alert itself.
- Page on symptoms users feel, not on every cause.
- Record the timeline while the incident is running.

## Project signals

`**/slo*.yaml`, `**/alerts/**`, `**/runbooks/**`, `prometheus.yml`, `**/grafana/**`
