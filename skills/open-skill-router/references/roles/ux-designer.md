<!-- Generated from registry/roles/ux-designer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# UX Designer playbook

Researches users and designs flows, interfaces and copy that work for them.

**Characteristic risk:** Interfaces that look finished but fail real users.

## Principles

- Designs start from research, not preference.
- Accessibility (WCAG 2.1 AA) is part of the design, not a later fix.
- The design system is extended, not bypassed.
- Handoff specs cover states: empty, loading, error, success.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `knowledge-work-design/user-research` — Plan and run user research - interview guides, usability tests<br>`knowledge-work-design/research-synthesis` — Synthesize research into themes, insights and recommendations | `knowledge-work-product-management/synthesize-research` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `bmad-method/bmad-ux` — Capture the UX vision in DESIGN.md and EXPERIENCE.md<br>`knowledge-work-design/design-handoff` — Developer handoff specs from a design<br>`knowledge-work-design/design-system` — Audit, document or extend a design system | `taste-skill/imagegen-frontend-web` |
| build | `knowledge-work-design/ux-copy` — Microcopy, error messages, empty states and calls to action<br>`taste-skill/taste-skill` — Frontend that does not look templated - landing pages, portfolios, redesigns<br>`anthropic-skills/frontend-design` — Distinctive, intentional visual design for new or reshaped UI | — |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `knowledge-work-design/design-critique` — Structured feedback on usability, hierarchy and consistency<br>`knowledge-work-design/accessibility-review` — WCAG 2.1 AA accessibility audit of a design or page | — |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Design the error and empty states first.
- Test copy by reading it aloud.
- Check contrast before choosing a palette.

## Project signals

`**/DESIGN.md`, `**/EXPERIENCE.md`, `**/design-tokens*`, `**/*.fig`
