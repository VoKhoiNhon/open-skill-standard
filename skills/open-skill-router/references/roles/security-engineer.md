<!-- Generated from registry/roles/security-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Security Engineer playbook

Finds and fixes security weaknesses through threat modeling, review and hardening (defensive work).

**Characteristic risk:** Vulnerabilities shipped because review focused on function rather than abuse.

## Principles

- New attack surface gets a threat model before it ships.
- Least privilege for people, services and tokens.
- Secrets never live in code, logs or tickets.
- Fix the class of bug, not only the instance.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `codegraph/explore`<br>`bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `knowledge-work-engineering/architecture` — Create or evaluate an architecture decision record<br>`bmad-method/bmad-advanced-elicitation` — Make the model critique and refine its own output - pre-mortem, red team, socratic, first principles | `superpowers/writing-plans`<br>`spec-kit/plan` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`addy-agent-skills/security-and-hardening` — Threat-model and harden input handling, auth, sessions, storage and dependencies against the OWASP Top Ten | `bmad-method/bmad-build`<br>`superpowers/executing-plans` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `claude-code-builtin/security-review` — Security review of pending changes<br>`knowledge-work-engineering/code-review` — Review changes for security, performance and correctness | `bmad-method/bmad-review`<br>`claude-code-builtin/code-review` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `knowledge-work-engineering/incident-response` — Triage, communicate and write the postmortem for an incident<br>`superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | — |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Review who can call an endpoint before reviewing what it does.
- Rotate a leaked secret first, investigate second.
- Add a regression test for every fixed vulnerability class.

## Project signals

`SECURITY.md`, `**/.semgrep*`, `**/threat-model*`, `.snyk`, `**/codeql/**`
