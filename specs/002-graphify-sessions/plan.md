# Implementation Plan: Parallel sessions on one shared project graph

**Branch**: `002-graphify-sessions` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-graphify-sessions/spec.md`

## Summary

Several agent sessions on one project share a single Graphify code graph and declare the paths they work on. `open-skill session update` refreshes that graph through Graphify, which already serializes rebuilds with its own lock. It then takes the files changed since the session's start commit from git and walks the graph backwards for up to two hops over calls, references and imports, resolving `from pkg import mod` to the module because Graphify links it to the package, and warns, without ever blocking, when a reached file lies in another active session's scope. Two new adapters make Graphify's tools and the session check routable. Codegraph stays unchanged.

## Technical Context

**Language/Version**: Python ≥ 3.11 (`pyproject.toml`)

**Primary Dependencies**: standard library only (`json`, `secrets`, `subprocess`, `fnmatch`, `datetime`). PyYAML and jsonschema are already present. Graphify ≥ 0.9.72 is an external CLI the user installs; it is never a Python import.

**Storage**: JSON files in `<project>/.open-skill/sessions/`; Graphify's `graphify-out/graph.json`, read only

**Testing**: pytest with a fake `graphify` executable on `PATH` and a small fixture graph; routing evals (`open-skill eval`)

**Target Platform**: macOS and Linux. Windows works without the session-record lock, the same limit the knowledge store has today.

**Project Type**: CLI and library (`cli/open_skill/`)

**Performance Goals**: refresh plus conflict check under 5 s on this repo (SC-001). Measured parts: `graphify update` ~2.4 s; the walk over ~2.2k nodes and ~3.6k edges, including resolving package imports, took 4–10 ms in a prototype (R5).

**Constraints**: never block or fail on a conflict; never run a full build or `--force` on the user's behalf; no network

**Scale/Scope**: a handful of sessions per project; graphs up to Graphify's own limits (the walk is linear in edges)

## Constitution Check

*GATE: must pass before Phase 0 research, and again after Phase 1 design.*

| Principle | Status | How |
|---|---|---|
| I. Agent-agnostic | ✅ | Sessions are plain files keyed by an open-skill id, not by any agent's session id (R8). The Graphify tools are described in an adapter. |
| II. Data over prompts | ✅ | Routing is done by adapter YAML plus new eval cases; the only skill text added is one paragraph in `open-skill-intel`. |
| III. Integrate, never vendor | ✅ | Graphify is called as a CLI and described by metadata with its upstream link and license; none of its code is copied. |
| IV. Local-first user data | ✅ | Session records stay in the project, self-ignored by git (R10). Nothing is sent anywhere. |
| V. Evidence for every claim | ✅ | `tested_version: 0.9.72`; every behavior relied on (lock, atomic write, exit codes, graph format) is checked and cited in research.md. |
| VI. Model-neutral skills | ✅ | The added intel paragraph names no model. |
| VII. Simplest thing first | ✅ | No new dependency, no daemon, no second graph lock (R2); the existing lock helper and glob matcher are reused (R3, R7). |

Quality gates stay as they are: tests, evals, `validate`, `lint skills/`, `build --check`, privacy guard.

**Post-design re-check**: still ✅. Phase 1 removed one lock (R2) and added no new component.

## Project Structure

### Documentation (this feature)

```text
specs/002-graphify-sessions/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R10
├── data-model.md        # session record, refresh result
├── quickstart.md        # validation runs
├── contracts/cli.md     # commands, output, exit codes, registry entries
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks, not yet created
```

### Source Code (repository root)

```text
cli/open_skill/
├── paths.py             # + locked(path), moved from knowledge._locked (R3)
├── knowledge.py         # uses paths.locked(home() / ".lock")
├── sessions.py          # NEW: start/end/active/prune, overlaps, affected-files walk, update()
├── project.py           # inspect() also returns "graphify"
├── route.py             # line 361: report "graphify" with "codegraph"
└── cli.py               # + `session` command with start/list/end/update

registry/adapters/
├── graphify.yaml        # NEW: query, affected, update tools
└── open-skill-cli.yaml  # NEW: session-update tool (R9)

spec/taxonomy.yaml       # tool_markers.graphify
skills/open-skill-intel/SKILL.md   # one paragraph: scope graph questions to the session

tests/
├── test_sessions.py         # NEW: records, staleness, overlap, prune, concurrent start
├── test_session_update.py   # NEW: fake graphify, walk, conflicts, --json, error paths
├── fixtures/graphify/graph.json   # NEW: small graph incl. an imports-only test file
└── test_project.py          # + graphify marker

evals/routing.yaml       # + 2–3 cases (session conflict, graphify affected)
README.md, README.vi.md, CHANGELOG.md
```

**Structure Decision**: One new module, `sessions.py`, of about 150 lines, which the `session` subcommands in `cli.py` call. The walk lives in the same module because nothing else uses it; split it out when a second caller appears. Generated outputs (`dist/`, playbooks, schemas) are refreshed by `open-skill build`, which covers the new adapters.

## Complexity Tracking

No constitution violations; nothing to justify.
