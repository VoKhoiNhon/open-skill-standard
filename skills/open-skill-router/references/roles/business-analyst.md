<!-- Generated from registry/roles/business-analyst.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Business Analyst playbook

Turns business needs into clear, testable requirements and process models.

**Characteristic risk:** Ambiguous requirements that each team reads differently.

## Principles

- Every requirement is testable and has acceptance criteria.
- Ambiguities are resolved with stakeholders, not assumed.
- Process changes are modeled before they are built.
- Requirements trace to the business goal they serve.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `knowledge-work-product-management/synthesize-research` — Turn interviews, surveys and feedback into structured insights<br>`bmad-method/bmad-agent-analyst` — Business analyst persona for research and requirements<br>`bmad-method/bmad-deep-recon` — Decision research - market, domain, technical, competitive, academic, with cited sources | `knowledge-work-design/user-research` |
| specify | `knowledge-work-product-management/write-spec` — Feature spec or PRD from a problem statement or idea<br>`bmad-method/bmad-prd` — Create, update or validate a PRD<br>`spec-kit/specify` — Write the feature specification - what and why, not how | `spec-kit/clarify`<br>`bmad-method/bmad-spec` |
| plan | `bmad-method/bmad-ticket` — Slice initiatives into epics and stories and run the board | `knowledge-work-product-management/sprint-planning` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `spec-kit/checklist` — Generate a requirements-quality checklist for the feature<br>`spec-kit/analyze` — Cross-check spec, plan and tasks for consistency before implementing<br>`knowledge-work-data/validate-data` — QA an analysis or dataset before sharing - methodology, accuracy, bias | `bmad-method/bmad-advanced-elicitation` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`superpowers/requesting-code-review` — Ask for a review of finished work before merging | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review`<br>`knowledge-work-engineering/code-review` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Write acceptance criteria as Given/When/Then.
- List who signs off on each requirement.
- Ask for a real example for every rule.

## Project signals

`**/requirements*.md`, `**/*.bpmn`, `**/user-stories*.md`
