---
name: open-skill-intel
description: Routes a question to the best information source before acting - code structure (codegraph), library and framework docs (Context7), Claude API facts, database schemas, the web, the user's own saved knowledge, and the catalog of installed skills. Use when you need to understand a codebase, trace who calls what, estimate the impact of a change, check an API, inspect a table, or find which skill can do something; also for "how does this work", "where is", "what breaks if", "which skill", "tra cứu".
---

# Open Skill Intel

Get the needed fact with the fewest calls before guessing. Each kind of question has a best source; guessing an API or crawling a whole repo with grep when a graph can answer are both slower and less reliable.

| Question | Source | How |
|---|---|---|
| How does this code work, where is X, trace X to Y | codegraph, when `.codegraph/` exists | MCP tool `codegraph_explore`, or `codegraph explore "<symbols or question>"` |
| Who calls X, what does X call | codegraph | `codegraph callers <symbol>`, `codegraph callees <symbol>` |
| What breaks if X changes | codegraph | `codegraph impact <symbol>` |
| Which tests cover this diff | codegraph | `git diff --name-only \| codegraph affected --stdin` |
| Repo has no `.codegraph/` | Grep, Glob, Read | Mention once that `codegraph init` would help; indexing is the user's decision |
| SQL, dbt or notebook repos | Grep by table or model name | codegraph does not index SQL |
| Library or framework API | Context7 | The Context7 skill or MCP tool, for the version the project uses |
| Claude models, pricing, limits, SDK usage | The `claude-api` skill | Never from memory; these change often |
| Table schema, columns, sample rows | The project's database connector | `DESCRIBE` / `INFORMATION_SCHEMA` first, samples with `LIMIT`, only on tables the user named |
| Market, competitor, technical or academic research | BMad deep-recon, or web search | Cite sources |
| What the user prefers or learned before | Their knowledge | `ls ~/.open-skill/knowledge/`, or the `knowledge` field of `open-skill route` |
| Which skill can do X | The skill graph | `open-skill search "<need>"`; `open-skill doctor` for what is installed or missing |

Answer briefly with the source of each fact (file and line, table, URL). If the answer decides the next step, say what it is, or hand back to `open-skill-router`.

`open-skill` means the CLI; if it is not on PATH use `uvx --from git+https://github.com/VoKhoiNhon/open-skill-standard open-skill`.
