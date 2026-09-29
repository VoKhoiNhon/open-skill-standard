<!-- Generated from registry/roles/system-administrator.yaml by `open-skill build`. Edit the YAML, not this file. -->

# System Administrator playbook

Runs servers, operating systems, identity and internal services.

**Characteristic risk:** Undocumented manual changes that cannot be reproduced or audited.

## Principles

- Changes are scripted and idempotent.
- Procedures live in runbooks next to the scripts.
- Systems are patched on a schedule.
- Backups are verified by restoring them.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec<br>`spec-kit/tasks` — Generate a dependency-ordered tasks.md from the plan | `bmad-method/bmad-ticket`<br>`knowledge-work-engineering/system-design` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`ponytail/ponytail` — Take the laziest solution that works - stdlib and native features before new code or dependencies | `bmad-method/bmad-build`<br>`spec-kit/implement` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`superpowers/requesting-code-review` — Ask for a review of finished work before merging | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review`<br>`knowledge-work-engineering/code-review` |
| release | `knowledge-work-engineering/deploy-checklist` — Pre-deployment verification for releases, migrations and flags | `knowledge-work-engineering/documentation` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix<br>`knowledge-work-engineering/incident-response` — Triage, communicate and write the postmortem for an incident | `claude-code-builtin/schedule` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Run a playbook twice; the second run must change nothing.
- Write the runbook step before automating it.
- Keep a change log for every production host.

## Project signals

`ansible.cfg`, `**/playbooks/**`, `**/*.service`, `inventory*`, `**/crontab*`
