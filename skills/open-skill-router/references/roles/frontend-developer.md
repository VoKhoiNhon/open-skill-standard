<!-- Generated from registry/roles/frontend-developer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Frontend Developer playbook

Builds user interfaces for the web: components, state, styling, accessibility and performance.

**Characteristic risk:** UI that works on the author's machine but breaks on real devices, browsers, or for keyboard and screen-reader users.

## Principles

- Accessible by default: keyboard operable, labelled, sufficient contrast.
- The UI is verified running in a browser before it is called done.
- Performance budget: bundle size and interaction latency are measured, not guessed.
- Native platform features before new dependencies.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec | `knowledge-work-design/design-handoff`<br>`bmad-method/bmad-ux` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`taste-skill/taste-skill` — Frontend that does not look templated - landing pages, portfolios, redesigns<br>`anthropic-skills/frontend-design` — Distinctive, intentional visual design for new or reshaped UI | `taste-skill/redesign-skill`<br>`spec-kit/implement`<br>`bmad-method/bmad-build` |
| verify | `claude-code-builtin/run` — Launch and drive the project's app to see a change working<br>`anthropic-skills/webapp-testing` — Drive and test local web apps with Playwright<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `knowledge-work-design/accessibility-review`<br>`codegraph/affected` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`knowledge-work-design/accessibility-review` — WCAG 2.1 AA accessibility audit of a design or page | `knowledge-work-design/design-critique`<br>`ponytail/ponytail-review` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Try the page with the keyboard only before calling it done.
- Prefer native elements (button, input type=date, dialog) over custom widgets.
- Read the docs for the installed library version before using an API.

## Project signals

`package.json`, `**/*.tsx`, `**/*.jsx`, `**/*.vue`, `**/*.svelte`, `vite.config.*`, `next.config.*`
