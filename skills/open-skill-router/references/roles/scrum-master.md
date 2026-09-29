<!-- Generated from registry/roles/scrum-master.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Scrum Master / Agile Coach playbook

Facilitates planning, flow and continuous improvement for delivery teams.

**Characteristic risk:** Ceremonies without outcomes: work that looks planned but does not flow.

## Principles

- Sprint goals are outcomes the team can explain.
- Blockers are raised the day they appear.
- Retrospectives produce few, owned, followed-up actions.
- Flow metrics (cycle time, WIP) are visible.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `knowledge-work-product-management/sprint-planning` — Scope work, estimate capacity and draft a sprint plan<br>`bmad-method/bmad-ticket` — Slice initiatives into epics and stories and run the board | `bmad-method/bmad-correct-course` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`superpowers/requesting-code-review` — Ask for a review of finished work before merging | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review`<br>`knowledge-work-engineering/code-review` |
| release | `knowledge-work-product-management/stakeholder-update` — Status update tailored to audience and cadence | — |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `bmad-method/bmad-retrospective` — Evidence-based retrospective of a finished epic<br>`knowledge-work-engineering/standup` — Standup update from recent activity | `open-skill/open-skill-learn` |

## Starter knowledge

- Limit work in progress before adding process.
- Bring last retro's actions to the next retro.
- Make one change at a time and measure it.

## Project signals

`**/sprint*.md`, `**/retro*.md`, `**/board*.md`
