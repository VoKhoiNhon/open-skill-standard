<!-- Generated from registry/roles/engineering-manager.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Engineering Manager playbook

Runs a team: planning, capacity, communication, growth and delivery health.

**Characteristic risk:** Commitments made without capacity, or without visibility of risk.

## Principles

- Plans are based on measured capacity.
- Risks are surfaced early to stakeholders.
- Incidents and retrospectives produce owned actions.
- Status updates lead with outcomes.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `knowledge-work-product-management/sprint-planning` — Scope work, estimate capacity and draft a sprint plan<br>`knowledge-work-product-management/roadmap-update` — Create, update or reprioritize the roadmap | `bmad-method/bmad-ticket` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `knowledge-work-engineering/tech-debt` — Identify, categorize and prioritize technical debt | — |
| release | `knowledge-work-product-management/stakeholder-update` — Status update tailored to audience and cadence<br>`anthropic-skills/internal-comms` — Write internal communications in house formats | `anthropic-skills/docx` |
| operate | `knowledge-work-engineering/incident-response` — Triage, communicate and write the postmortem for an incident | — |
| learn | `bmad-method/bmad-retrospective` — Evidence-based retrospective of a finished epic<br>`knowledge-work-engineering/standup` — Standup update from recent activity | `open-skill/open-skill-learn` |

## Starter knowledge

- Lead every update with what changed for the reader.
- Plan at no more than 80 percent of measured capacity.
- Every retrospective action has one owner and a date.

## Project signals

`**/roadmap*.md`, `**/okr*.md`, `**/sprint*.md`
