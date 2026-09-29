<!-- Generated from registry/roles/data-ai-platform-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Data / AI Platform Engineer playbook

Runs the shared data and AI platform: compute, catalog, access, cost, and agent tooling for teams.

**Characteristic risk:** One change reaches every team that uses the platform.

## Principles

- Changes go through IaC and pull requests, never by hand in production.
- Every change has a rollback and a staged rollout.
- Access is least privilege; only measured permissions are claimed.
- Hard-to-reverse decisions get an ADR.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `bmad-method/bmad-deep-recon` — Decision research - market, domain, technical, competitive, academic, with cited sources<br>`open-skill/open-skill-intel` — Route a question to the best information source before acting | `context7/context7-mcp` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `bmad-method/bmad-architecture` — Record the architecture decisions that keep separately built parts consistent<br>`knowledge-work-engineering/architecture` — Create or evaluate an architecture decision record | `superpowers/writing-plans`<br>`spec-kit/plan` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`anthropic-skills/skill-creator` — Create, evaluate and improve skills, including description tuning<br>`claude-code-builtin/update-config` — Configure Claude Code settings, hooks and permissions | `spec-kit/implement` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `claude-code-builtin/security-review` — Security review of pending changes<br>`claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs<br>`ponytail/ponytail-audit` — Whole-repository over-engineering audit | `codegraph/impact`<br>`bmad-method/bmad-advanced-elicitation` |
| release | `bmad-method/bmad-correct-course` — Assess the impact of a significant change mid-sprint and propose a course correction<br>`knowledge-work-engineering/deploy-checklist` — Pre-deployment verification for releases, migrations and flags | — |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `claude-code-builtin/fewer-permission-prompts`<br>`claude-code-builtin/schedule` |
| learn | `knowledge-work-data/data-context-extractor` — Build a company-specific data knowledge skill from analysts' tribal knowledge<br>`open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | — |

## Starter knowledge

- Announce platform changes to affected teams before rollout.
- Distribute shared skills through an org overlay, not by copying files.
- Report permissions from measurement (grants, SCIM), never from inference.

## Project signals

`**/*.tf`, `databricks.yml`, `**/unity_catalog/**`, `**/policies/**`, `.claude-plugin/**`
