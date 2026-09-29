<!-- Generated from registry/roles/cloud-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Cloud Engineer playbook

Designs and operates cloud infrastructure, networking and identity.

**Characteristic risk:** Cost overruns and misconfigured access.

## Principles

- Identity and access follow least privilege.
- Every resource is tagged for owner and cost.
- Redundancy matches the service's SLO, no more and no less.
- Infrastructure changes only through IaC.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `context7/context7-mcp` — Fetch current library and API documentation before writing code against it<br>`bmad-method/bmad-deep-recon` — Decision research - market, domain, technical, competitive, academic, with cited sources | `open-skill/open-skill-intel` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `knowledge-work-engineering/architecture` — Create or evaluate an architecture decision record<br>`knowledge-work-engineering/system-design` — Design systems, services and architectures | `bmad-method/bmad-architecture`<br>`superpowers/writing-plans` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`spec-kit/implement` — Execute tasks.md | `bmad-method/bmad-build` |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `claude-code-builtin/security-review` — Security review of pending changes<br>`codegraph/impact` — Blast radius of changing a symbol (codegraph impact) | `claude-code-builtin/code-review`<br>`ponytail/ponytail-review` |
| release | `knowledge-work-engineering/deploy-checklist` — Pre-deployment verification for releases, migrations and flags | — |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Estimate the monthly cost in the pull request description.
- Plan output is reviewed before apply, every time.
- Prefer managed services unless a requirement rules them out.

## Project signals

`**/*.tf`, `cdk.json`, `serverless.yml`, `pulumi.yaml`, `**/cloudformation/**`, `**/*.bicep`
