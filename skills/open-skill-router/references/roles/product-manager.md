<!-- Generated from registry/roles/product-manager.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Product Manager playbook

Decides what to build and why, and measures whether it worked.

**Characteristic risk:** Building the wrong thing well.

## Principles

- Problems are validated with evidence before solutions are specified.
- Specs state the user, the problem, success metrics and non-goals.
- Roadmaps show outcomes, not only features.
- Launched work is measured against its success metric.

## Skills by phase

Build tasks for this role walk discover → research → specify → plan, instead of plan → build → verify → review.

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `knowledge-work-product-management/product-brainstorming` — Explore problem spaces and challenge assumptions as a thinking partner<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped<br>`bmad-method/bmad-prfaq` — Working-backwards press release and FAQ to test a product concept | `bmad-method/bmad-party-mode` |
| research | `knowledge-work-product-management/competitive-brief` — Competitive analysis for a feature area or competitors<br>`knowledge-work-product-management/synthesize-research` — Turn interviews, surveys and feedback into structured insights<br>`bmad-method/bmad-deep-recon` — Decision research - market, domain, technical, competitive, academic, with cited sources | `knowledge-work-design/user-research` |
| specify | `knowledge-work-product-management/write-spec` — Feature spec or PRD from a problem statement or idea<br>`bmad-method/bmad-prd` — Create, update or validate a PRD<br>`spec-kit/specify` — Write the feature specification - what and why, not how | `bmad-method/bmad-product-brief`<br>`spec-kit/clarify` |
| plan | `knowledge-work-product-management/roadmap-update` — Create, update or reprioritize the roadmap<br>`bmad-method/bmad-ticket` — Slice initiatives into epics and stories and run the board | `knowledge-work-product-management/sprint-planning` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `knowledge-work-product-management/metrics-review` — Review product metrics with trends and actionable insights<br>`knowledge-work-data/analyze` — Answer data questions from quick lookups to full analyses | — |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`superpowers/requesting-code-review` — Ask for a review of finished work before merging | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review`<br>`knowledge-work-engineering/code-review` |
| release | `knowledge-work-product-management/stakeholder-update` — Status update tailored to audience and cadence | `anthropic-skills/pptx`<br>`anthropic-skills/docx` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Write the non-goals before the goals.
- Name the metric that would prove the feature failed.
- Talk to five users before writing the spec.

## Project signals

`**/prd*.md`, `**/roadmap*.md`, `**/specs/**`
