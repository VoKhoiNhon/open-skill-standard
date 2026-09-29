<!-- Generated from registry/roles/embedded-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Embedded Engineer playbook

Writes firmware and low-level software for microcontrollers and devices.

**Characteristic risk:** Timing, memory and hardware assumptions that fail on the real board.

## Principles

- Resource budgets (RAM, flash, CPU) are declared and measured on target.
- Calibration values stay configurable; real hardware drifts.
- Behavior is tested on target hardware, not only on the host.
- The device fails safe on sensor or bus errors.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec<br>`spec-kit/tasks` — Generate a dependency-ordered tasks.md from the plan | `bmad-method/bmad-ticket`<br>`knowledge-work-engineering/system-design` |
| build | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks | `bmad-method/bmad-build`<br>`ponytail/ponytail` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`ponytail/ponytail-review` — Review a diff only for over-engineering and what to delete | `bmad-method/bmad-review` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Keep calibration constants configurable; real sensors read off.
- Measure stack and heap on target after each feature.
- Guard every blocking wait with a timeout.

## Project signals

`platformio.ini`, `**/*.ino`, `CMakeLists.txt`, `**/*.ld`, `sdkconfig`, `Kconfig`
