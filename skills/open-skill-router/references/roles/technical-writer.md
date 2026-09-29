<!-- Generated from registry/roles/technical-writer.yaml by `open-skill build`. Edit the YAML, not this file. -->

# Technical Writer playbook

Writes and maintains documentation that lets people use and change a system.

**Characteristic risk:** Documentation that is wrong, stale or written for the author instead of the reader.

## Principles

- Every page has a stated reader and task.
- Examples are tested against the current version.
- Docs change in the same pull request as the behavior.
- Plain language over jargon.

## Skills by phase

Build tasks for this role walk research → release → review, instead of plan → build → verify → review.

| Phase | Primary | Alternatives |
|---|---|---|
| discover | `superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building<br>`bmad-method/bmad-forge-idea` — Pressure-test a half-formed idea with personas until it can be acted on or dropped | `bmad-method/bmad-brainstorming`<br>`knowledge-work-product-management/product-brainstorming` |
| research | `open-skill/open-skill-intel` — Route a question to the best information source before acting<br>`codegraph/explore` — Answer how code works, trace flows and read symbols with call paths (MCP codegraph_explore)<br>`context7/context7-mcp` — Fetch current library and API documentation before writing code against it | — |
| specify | `spec-kit/specify` — Write the feature specification - what and why, not how<br>`superpowers/brainstorming` — Converge an idea into an approved design through one-question-at-a-time dialogue before building | `bmad-method/bmad-spec`<br>`knowledge-work-product-management/write-spec` |
| plan | `superpowers/writing-plans` — Turn a spec into a bite-sized, test-first implementation plan<br>`spec-kit/plan` — Create the technical plan and design artifacts from the spec<br>`spec-kit/tasks` — Generate a dependency-ordered tasks.md from the plan | `bmad-method/bmad-ticket`<br>`knowledge-work-engineering/system-design` |
| build | `knowledge-work-design/ux-copy` — Microcopy, error messages, empty states and calls to action | — |
| verify | `superpowers/test-driven-development` — Write the failing test first, then the minimal code, for any feature or bug fix<br>`superpowers/verification-before-completion` — Run the real checks and read their output before claiming work is done | `codegraph/affected`<br>`spec-kit/converge` |
| review | `bmad-method/bmad-review` — Review lenses - adversarial, edge cases, verification gaps, structure, prose | `claude-code-builtin/code-review`<br>`knowledge-work-design/design-critique` |
| release | `knowledge-work-engineering/documentation` — Write and maintain technical documentation and READMEs<br>`anthropic-skills/doc-coauthoring` — Structured workflow for co-writing documentation | `anthropic-skills/docx`<br>`anthropic-skills/pdf` |
| operate | `superpowers/systematic-debugging` — Find the root cause of a bug, failing test or unexpected behavior before proposing a fix | `knowledge-work-engineering/debug`<br>`spec-kit/bug-assess` |
| learn | `open-skill/open-skill-learn` — Remember lessons and preferences so future routes use them | `bmad-method/bmad-retrospective` |

## Starter knowledge

- Start each page with what the reader will be able to do.
- Run every code sample before publishing.
- Link to the source of truth instead of copying it.

## Project signals

`docs/**`, `mkdocs.yml`, `docusaurus.config.*`, `**/*.mdx`
