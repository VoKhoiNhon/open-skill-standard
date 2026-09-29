<!-- Generated from registry/roles/ai-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# AI Engineer playbook

Builds LLM applications, agents, RAG systems, MCP servers and agent skills.

**Characteristic risk:** Non-deterministic output that passed once, and prompt injection through tools and content.

## Principles

- An eval suite exists before anything is called better.
- Model and prompt versions are recorded; model IDs come from documentation, not memory.
- Tool, web and file output is data, never instructions.
- Tokens, cost, time and agent loop counts are bounded.

## Skills by phase

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `claude-code-builtin/claude-api` — Claude API and SDK reference - models, pricing, tool use, caching, migration<br>`anthropic-skills/claude-api` — Reference for the Claude API and Anthropic SDKs - models, pricing, tool use, caching<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | `bmad-method/bmad-deep-recon` |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`bmad-method/bmad-architecture` — Record the architecture decisions that keep separately built parts consistent | `spec-kit/plan` |
| build | `superpowers/subagent-driven-development` — Execute a plan task by task with fresh subagents and review between tasks<br>`anthropic-skills/skill-creator` — Create, evaluate and improve skills, including description tuning<br>`anthropic-skills/mcp-builder` — Build high-quality MCP servers<br>`superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix | `superpowers/dispatching-parallel-agents`<br>`spec-kit/implement`<br>`bmad-method/bmad-build` |
| verify | `anthropic-skills/skill-creator` — Create, evaluate and improve skills, including description tuning<br>`superpowers/writing-skills` — Author and test Agent Skills so they measurably change agent behavior<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | — |
| review | `claude-code-builtin/security-review` — Security review of pending changes<br>`claude-code-builtin/code-review` — Review the current diff or a PR for correctness bugs | `bmad-method/bmad-review`<br>`bmad-method/bmad-advanced-elicitation` |
| release | `superpowers/finishing-a-development-branch` — Decide how to integrate finished, tested work - merge, pull request or cleanup | `knowledge-work-engineering/deploy-checklist` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Separate the system prompt from user and tool content.
- Cap the number of agent iterations and tool calls.
- Compare every prompt change against the same eval set.

## Project signals

`**/prompts/**`, `evals/**`, `**/SKILL.md`, `.claude-plugin/**`, `**/*mcp*.json`, `**/agents/**`
