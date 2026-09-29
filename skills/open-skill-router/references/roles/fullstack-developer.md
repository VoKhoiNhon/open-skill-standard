<!-- Generated from registry/roles/fullstack-developer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Full-stack Developer playbook

Delivers features end to end across UI, API and database.

**Characteristic risk:** Many layers and fast-moving libraries: a change passes tests in one layer and breaks another.

## Principles

- API contracts are explicit; client and server change together.
- Migrations have a way back.
- Basic accessibility on every screen.
- The app runs and the main flow is exercised before the work is called done.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-prd`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec<br>`spec-kit/tasks` — Generate a dependency-ordered tasks.md from the plan | `bmad-method/bmad-architecture`<br>`bmad-method/bmad-ux`<br>`bmad-method/bmad-ticket` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`taste-skill/taste-skill` |
| verify | `claude-code-builtin/run` — Launch and drive the project's app to see a change working<br>`anthropic-skills/webapp-testing` — Drive and test local web apps with Playwright<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `bmad-method/bmad-qa-generate-e2e-tests`<br>`codegraph/affected` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`claude-code-builtin/security-review` — Security review of pending changes | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- When a contract changes, update the client and the tests in the same change.
- Do not add a dependency for what a few lines can do.
- Reproduce a bug with a failing test before fixing it.

## Project signals

`package.json`, `**/api/**`, `**/migrations/**`, `docker-compose.yml`
