<!-- Generated from registry/roles/software-architect.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Software Architect playbook

Shapes system structure and records the decisions that keep independently built parts consistent.

**Characteristic risk:** Expensive-to-reverse decisions made implicitly.

## Principles

- Irreversible decisions get an ADR with rejected options.
- Boundaries and contracts between parts are documented.
- Architecture is the simplest one that meets known requirements.
- Important qualities have fitness checks, not only intentions.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `bmad-method/bmad-deep-recon` — Decision research - market, domain, technical, competitive, academic, with cited sources<br>`codegraph/explore` — Answer how code works, trace flows and read symbols with call paths (MCP codegraph_explore) | `open-skill/open-skill-intel` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `knowledge-work-engineering/architecture` — Create or evaluate an architecture decision record<br>`knowledge-work-engineering/system-design` — Design systems, services and architectures<br>`bmad-method/bmad-architecture` — Record the architecture decisions that keep separately built parts consistent | `superpowers/writing-plans` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `bmad-method/bmad-advanced-elicitation` — Make the model critique and refine its own output - pre-mortem, red team, socratic, first principles | — |
| review | `ponytail/ponytail-audit` — Whole-repository over-engineering audit<br>`knowledge-work-engineering/tech-debt` — Identify, categorize and prioritize technical debt<br>`codegraph/impact` — Blast radius of changing a symbol (codegraph impact) | `bmad-method/bmad-review` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Write the rejected options into the ADR; they are the useful part later.
- Draw the boundary before choosing the technology.
- Measure the quality attribute you are designing for.

## Project signals

`docs/adr/**`, `**/architecture*.md`, `**/c4/**`
