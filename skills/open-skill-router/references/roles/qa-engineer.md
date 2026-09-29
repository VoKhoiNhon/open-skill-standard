<!-- Generated from registry/roles/qa-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# QA / Test Engineer playbook

Designs test strategy and automation so the product's behavior is known, not assumed.

**Characteristic risk:** Tests that pass while the product is broken.

## Principles

- Tests assert user-visible behavior, not implementation details.
- A flaky test is a bug and gets fixed or quarantined with an owner.
- Coverage follows risk, not a percentage target.
- Every bug fix starts with a failing test that reproduces it.

## Skills by phase

Build tasks for this role walk plan → build → verify → review, instead of plan → build → verify → review.

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `knowledge-work-engineering/testing-strategy` — Design test strategies and test plans | `spec-kit/checklist`<br>`superpowers/writing-plans` |
| build | `bmad-method/bmad-qa-generate-e2e-tests` — Generate API and end-to-end tests for implemented features<br>`anthropic-skills/webapp-testing` — Drive and test local web apps with Playwright<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | — |
| verify | `anthropic-skills/webapp-testing` — Drive and test local web apps with Playwright<br>`codegraph/affected` — Test files affected by changed source files (codegraph affected)<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `spec-kit/converge` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs | `bmad-method/bmad-review` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `spec-kit/bug-assess`<br>`knowledge-work-engineering/debug` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Name each test after the behavior it protects.
- Run the affected tests for a diff before running everything.
- Keep test data factories next to the tests that use them.

## Project signals

`playwright.config.*`, `cypress.config.*`, `tests/e2e/**`, `jest.config.*`, `pytest.ini`, `**/*.feature`
