<!-- Generated from registry/roles/mobile-developer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Mobile Developer playbook

Builds native or cross-platform apps for phones and tablets.

**Characteristic risk:** Behavior that differs across OS versions, devices and offline conditions.

## Principles

- Test on the smallest supported device and the oldest supported OS.
- Offline and slow networks are handled, not assumed away.
- Platform guidelines and permission prompts are respected.
- Releases go out as staged rollouts.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`knowledge-work-design/design-handoff` — Developer handoff specs from a design | `taste-skill/imagegen-frontend-mobile`<br>`spec-kit/plan` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `claude-code-builtin/run` — Launch and drive the project's app to see a change working<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `knowledge-work-design/accessibility-review` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`superpowers/requesting-code-review` — Ask for a review of finished work before merging | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review`<br>`knowledge-work-engineering/code-review` |
| release | `knowledge-work-engineering/deploy-checklist` — Pre-deployment verification for releases, migrations and flags<br>`superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | — |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Check behavior with airplane mode on before release.
- Ask for a permission at the moment it is needed, with context.
- Keep the minimum supported OS in the project README.

## Project signals

`Podfile`, `**/*.xcodeproj/**`, `android/**`, `ios/**`, `pubspec.yaml`, `app.json`, `build.gradle.kts`
