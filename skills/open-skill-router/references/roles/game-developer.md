<!-- Generated from registry/roles/game-developer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Game Developer playbook

Builds gameplay, tools and rendering for games in engines or frameworks.

**Characteristic risk:** Frame-time regressions and gameplay bugs that only show up in play.

## Principles

- Each target platform has a frame-time budget that is checked.
- Features are playtested before they are called done.
- Deterministic game logic is separated from rendering.
- Large assets are versioned with LFS or the engine's asset system.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `bmad-method/bmad-brainstorming` — Divergent brainstorming session with 60+ creative techniques<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-forge-idea` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec<br>`spec-kit/tasks` — Generate a dependency-ordered tasks.md from the plan | `bmad-method/bmad-ticket`<br>`knowledge-work-engineering/system-design` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `claude-code-builtin/run` — Launch and drive the project's app to see a change working<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `superpowers/test-driven-development` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`superpowers/requesting-code-review` — Ask for a review of finished work before merging | `bmad-method/bmad-code-review`<br>`ponytail/ponytail-review`<br>`knowledge-work-engineering/code-review` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Profile a representative scene before and after a change.
- Keep gameplay rules testable without the renderer.
- Record the engine version with the project.

## Project signals

`project.godot`, `**/*.gd`, `**/*.uproject`, `ProjectSettings/**`, `**/*.unity`
