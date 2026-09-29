<!-- Generated from registry/roles/tech-lead.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Tech Lead playbook

Leads a team's technical direction, reviews, and delivery quality.

**Characteristic risk:** Velocity lost to unclear standards and unreviewed risk.

## Principles

- Small pull requests, reviewed within a day.
- The team shares one definition of done.
- Technical debt is tracked and scheduled, not hoped away.
- Knowledge is shared through walkthroughs, not held by one person.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`knowledge-work-engineering/system-design` — Design systems, services and architectures | `bmad-method/bmad-ticket`<br>`spec-kit/tasks` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`bmad-method/bmad-code-review` — Several independent reviewers in parallel, then triage<br>`superpowers/receiving-code-review` — Evaluate review feedback technically before acting on it | `knowledge-work-engineering/tech-debt`<br>`ponytail/ponytail-review` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `bmad-method/bmad-walkthrough` — Guide a human through a commit, PR, file or directory<br>`bmad-method/bmad-project-context` — Set up and audit a repository's AGENTS.md instructions and pitfalls<br>`bmad-method/bmad-retrospective` — Evidence-based retrospective of a finished epic | `open-skill/open-skill-learn` |

## Starter knowledge

- Review the tests first; they show what the author believes the code does.
- Keep a visible tech-debt list with an owner per item.
- Write the definition of done into the pull request template.

## Project signals

`CODEOWNERS`, `.github/pull_request_template.md`, `CONTRIBUTING.md`
