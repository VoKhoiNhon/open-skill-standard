---
description: "Task list for parallel sessions on one shared Graphify graph"
---

# Tasks: Parallel sessions on one shared project graph

**Input**: Design documents from `specs/002-graphify-sessions/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R10), data-model.md, contracts/cli.md, quickstart.md

**Tests**: Requested. FR-015, the success criteria and quickstart.md call for pytest suites with a fake `graphify` and a fixture graph. Within each story, write the tests first and see them fail.

**Organization**: grouped by user story. Session records (the data both US1 and US2 need) are foundational.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2, US3 from spec.md
- Paths are relative to the repository root (`open-skill-standard/`). Run Python with `.venv/bin/python`, pytest with `.venv/bin/pytest`.

---

## Phase 1: Setup (shared fixtures)

**Purpose**: test scaffolding that several stories use.

- [ ] T001 [P] Create the fixture graph `tests/fixtures/graphify/graph.json` in networkx node-link form, with top-level keys `directed`, `multigraph`, `graph`, `nodes` and `links`. It needs:
  - nodes with `id` and `source_file` for `pkg/route.py` (symbols `route_fit`, `route_target_phase`), `pkg/cli.py` (`cli_cmd_route`, which calls `route_target_phase`), `pkg/deep.py` (`deep_run`, which calls `cli_cmd_route`: two hops from route), `pkg/far.py` (`far_x`, which calls `deep_run`: three hops, must NOT be reached), `tests/test_route.py`, and an external node `Path` with `source_file: ""`;
  - a file node `tests_test_route` linked to `pkg_route` **only** by `relation: "imports_from"`, which is the case Graphify misses (R5);
  - `contains` links from each file node to its symbols. The walk must ignore them.
- [ ] T002 [P] Add a fake-Graphify helper to `tests/conftest.py`. The fixture `fake_graphify(tmp_path, monkeypatch, exit_code=0, stderr="")`:
  - writes an executable `graphify` script into `tmp_path/bin`;
  - makes that script append its argv to `tmp_path/graphify-calls.log` and exit with `exit_code`, printing `stderr`;
  - prepends `tmp_path/bin` to `PATH`.
  Also add a fixture `graph_project(tmp_path)`:
  - copies `tests/fixtures/graphify/graph.json` to `<project>/graphify-out/graph.json` and creates the source files it names;
  - runs `git init`, `git add -A` and `git commit` with `-c user.name=t -c user.email=t@t` so changed files can be simulated.

---

## Phase 2: Foundational (blocking)

**Purpose**: the lock helper and the session-record store that US1 and US2 both use.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

- [ ] T003 Move `_locked()` from `cli/open_skill/knowledge.py:103-116` to `cli/open_skill/paths.py` as `locked(path: Path)`:
  - it creates `path.parent` if missing and keeps the no-`fcntl` fallback and its `ponytail:` comment verbatim;
  - in `cli/open_skill/knowledge.py`, delete `_locked` and replace `with _locked():` with `with paths.locked(home() / ".lock"):`;
  - run `.venv/bin/pytest tests/test_knowledge.py -q`: it must stay green, including the concurrent-learn test (R3).
- [ ] T004 Write failing tests in `tests/test_sessions.py` for the record store in `cli/open_skill/sessions.py`:
  - **start**: `start(project, scope, task)` writes `<project>/.open-skill/sessions/<id>.json` with the fields `id`, `scope`, `task`, `started` and `seen`, where `id` is "6 lowercase hex characters, equal to the file name without `.json`", and writes `<project>/.open-skill/.gitignore` containing `*` (R10);
  - **scope validation**: a scope needs "at least one glob, relative to the project root, forward slashes, no `..` and not absolute". Otherwise raise `ValueError`;
  - **task validation**: task "1–200 characters; one line (newlines replaced by spaces)". An empty task raises `ValueError`; a longer one raises `ValueError`;
  - **active**: `active(project, now=...)` returns only records with `now - seen <= 6 h`, and skips unreadable files (invalid JSON, a missing field, or an `id` that differs from the file name);
  - **touch**: `touch(project, id)` refreshes `seen` of an active session and returns False, changing nothing, for an unknown or stale id;
  - **end**: `end(project, id)` deletes the record (stale ones too) and raises `KeyError` for an unknown id;
  - **prune**: `prune(project, now=...)` deletes stale and unreadable records, keeps active ones and returns the count;
  - **concurrency**: 8 processes calling `start` at once (via `multiprocessing`) leave 8 readable records (FR-014).
- [ ] T005 Implement the record store in `cli/open_skill/sessions.py`:
  - `STALE = dt.timedelta(hours=6)`;
  - ids from `secrets.token_hex(3)`, retried on collision (R8);
  - UTC ISO-8601 timestamps ending in `Z`;
  - every write under `paths.locked(<project>/.open-skill/sessions/.lock)`;
  - JSON written to a temp file and `os.replace`d.
  Make T004 pass.

**Checkpoint**: `.venv/bin/pytest tests/test_sessions.py tests/test_knowledge.py -q` is green.

---

## Phase 3: User Story 1 — Refresh the shared graph and see who my change affects (P1) 🎯 MVP

**Goal**: `open-skill session update [--session ID] [--project PATH] [--json]` refreshes the graph through Graphify, lists the affected files and warns about files inside other sessions' scopes, without ever failing because of a conflict.

**Independent Test**: With `graph_project` and `fake_graphify`, start sessions A (`pkg/route.py`) and B (`tests/**`) through `sessions.start`, modify `pkg/route.py`, then run `cli.main(["session", "update", "--session", A, "--project", p, "--json"])`. The result lists `tests/test_route.py` in `affected`, and in `conflicts` with `session` B.

### Tests for User Story 1 (write first, must fail)

- [ ] T006 [P] [US1] Write failing tests for the walk in `tests/test_session_update.py`. `affected_files(graph, changed)`:
  - returns `pkg/cli.py`, `pkg/deep.py` and `tests/test_route.py` for `changed=["pkg/route.py"]`;
  - never returns `pkg/far.py` (three hops) or the changed file itself;
  - ignores `contains` links and nodes with an empty `source_file`;
  - follows only `calls`, `indirect_call`, `references`, `imports` and `imports_from`, in reverse, for 2 hops (R5).
- [ ] T007 [P] [US1] Write failing tests for `changed_files(project)` in `tests/test_session_update.py`:
  - returns modified tracked files plus untracked files;
  - returns `None` in a folder that is not a git repository, and in a repository with no commits (R6).
- [ ] T008 [P] [US1] Write failing CLI tests in `tests/test_session_update.py`, following contracts/cli.md § `session update`:
  - **conflict** (Acceptance 1): A changes `pkg/route.py` and B owns `tests/**`. Text output has a line starting with `⚠ tests/test_route.py is in session <B>`; exit code 0;
  - **imports-only** (Acceptance 2): `tests/test_route.py` is reported although it is linked only by `imports_from`;
  - **no conflict** (Acceptance 3): output lists affected files and has no `⚠` line;
  - **`--json`** (Acceptance 4): stdout is exactly one JSON object with the keys `session`, `graph`, `changed`, `git`, `affected`, `conflicts` and `warnings`. Each conflict has `file`, `session`, `task` and `via`. A changed file inside another session's scope is a conflict with `via` equal to the file;
  - **own session excluded**: the `--session` owner's own scope never produces a conflict;
  - **activity**: `--session A` refreshes A's `seen`. An unknown or stale id adds the warning `session ID is unknown or stale; checked against all active sessions` and still exits 0;
  - **no Graphify**: `graphify` missing from PATH → exit 2, stderr contains `uv tool install graphifyy`;
  - **no graph**: missing `graphify-out/graph.json` → exit 2, stderr contains `graphify extract . --code-only`; the fake graphify log shows no call;
  - **refresh fails**: the fake exits 1 with stderr `Nothing to update or rebuild failed` → exit 1, stderr contains that text and `graphify update . --force`. The fake log never contains `--force` (open-skill never forces);
  - **not a git repo**: output contains `conflict check skipped`; exit 0;
  - **Graphify call**: the fake log shows exactly `update .`, run with the project root as cwd.

### Implementation for User Story 1

- [ ] T009 [US1] Implement in `cli/open_skill/sessions.py`:
  - `load_graph(project)`, which reads `graphify-out/graph.json` and uses only `nodes[].id`, `nodes[].source_file` and `links[].source|target|relation`;
  - `affected_files(graph, changed, hops=2)` as a reverse BFS over the five relations of R5;
  - `changed_files(project)` from `git diff --name-only HEAD` plus `git ls-files --others --exclude-standard`, returning `None` when git fails.
  Make T006 and T007 pass.
- [ ] T010 [US1] Implement `conflicts(project, files_with_via, exclude_id, now)` in `cli/open_skill/sessions.py`. A file conflicts when it matches a scope glob of another active session through `project._match` (R7). Return dicts with `file`, `session`, `task` and `via`.
- [ ] T011 [US1] Implement `update(project, session_id=None)` in `cli/open_skill/sessions.py`. It returns the *Refresh result* dict of data-model.md and follows the steps of contracts/cli.md:
  - read the install hint from the Graphify adapter's `install.cli` (loaded through `registry`), with the fallback `uv tool install graphifyy` when the adapter is missing;
  - run `subprocess.run(["graphify", "update", "."], cwd=project, capture_output=True, text=True)`, with no lock of its own (R2);
  - raise dedicated exceptions for missing Graphify, a missing graph and a failed refresh, so the CLI can map them to exit codes 2, 2 and 1;
  - `graph.nodes` and `graph.edges` are the counts read from `graph.json` after the refresh.
- [ ] T012 [US1] Add the `session` command with the `update` subcommand to `cli/open_skill/cli.py`, next to the other `sub.add_parser(...)` calls near line 748. Flags are `--session`, `--project` (default `.`) and `--json`.
  - Text output follows the example in contracts/cli.md: `graph:` line, `changed:`, `affected: N files` with indented paths, then one `⚠` line per conflict.
  - Warnings and notes go to stderr.
  - Map the exceptions from T011 to exit codes: missing Graphify and missing graph → 2, failed refresh → 1.
  - Make T008 pass.

**Checkpoint**: `.venv/bin/pytest tests/test_session_update.py -q` is green; US1 works with sessions created through the API.

---

## Phase 4: User Story 2 — Declare, list and end sessions (P2)

**Goal**: `session start | list [--prune] | end` from the command line, with overlap warnings.

**Independent Test**: In `tmp_path` holding a few files, run `start` twice with overlapping scopes (one warning), then `list`, `end` one of them, and `list` again (one left).

### Tests for User Story 2 (write first, must fail)

- [ ] T013 [P] [US2] Write failing CLI tests in `tests/test_sessions.py`, following contracts/cli.md:
  - **start**: `session start --scope "cli/**" --task "speed up fit"` prints the id alone on stdout line 1, and `--json` prints the record (Acceptance 1);
  - **overlap**: a second start with `--scope cli/open_skill/route.py` exits 0 and prints to stderr `warning: scope overlaps session <id> ("speed up fit"): cli/open_skill/route.py` (Acceptance 2);
  - **no match**: a glob that matches no file warns `warning: scope glob matches no file: <glob>`;
  - **bad input**: no `--scope`, an absolute glob or one with `..`, or an empty task → exit 2;
  - **list**: lists active sessions newest `seen` first; `--json` prints a list; `list` never changes `seen`; a record with `seen` 7 h ago is not listed (Acceptance 3);
  - **prune**: `list --prune` removes stale and unreadable records and prints `pruned N record(s)` to stderr (Acceptance 4);
  - **end**: `end <id>` removes the record; an unknown id → exit 2 with `open-skill: no such session: <id>` (Acceptance 5).

### Implementation for User Story 2

- [ ] T014 [US2] Implement `overlaps(project, scope, exclude_id=None)` and `unmatched(project, scope)` in `cli/open_skill/sessions.py`, using `project._files` and `project._match` (R7). The first returns `(session, task, sample_file)` tuples.
- [ ] T015 [US2] Add the `start`, `list` and `end` subcommands under `session` in `cli/open_skill/cli.py`:
  - flags: `--scope` (repeatable, required), `--task` (required), `--project`, `--json`, `--prune`;
  - text format of `list`: `<id>  seen <N>m ago  <first scope glob>  <task>`;
  - `ValueError` and `KeyError` map to exit code 2 with an `open-skill:` message.
  Make T013 pass.

**Checkpoint**: `.venv/bin/pytest tests/test_sessions.py -q` is green; US1 and US2 both work from the CLI.

---

## Phase 5: User Story 3 — The router and intel skill know about Graphify (P3)

**Goal**: projects with `graphify-out/` are detected, and Graphify's tools plus the session check are routable. Codegraph routing stays unchanged.

**Independent Test**: `.venv/bin/open-skill eval` passes all existing cases and the new ones.

### Tests for User Story 3 (write first, must fail)

- [ ] T016 [P] [US3] Add to `tests/test_project.py`: a project containing `graphify-out/` gives `inspect(...)["graphify"] is True`, and one without it gives False, while `codegraph` keeps its current behavior (Acceptance 1).
- [ ] T017 [P] [US3] Add these routing cases to `evals/routing.yaml` near line 345, in the existing one-line style:
  - `{id: dev-session-conflict, role: backend-developer, task: "which other session does my change affect", phase: review, files: [graphify-out/graph.json], include: [open-skill-cli/session-update]}`;
  - `{id: qa-graphify-affected, role: qa-engineer, task: "what is affected by my change in the graphify graph", phase: review, files: [graphify-out/graph.json], include_any: [graphify/affected, open-skill-cli/session-update]}`;
  - `{id: no-graphify-no-tools, role: backend-developer, task: "which other session does my change affect", phase: review, exclude: [open-skill-cli/session-update, graphify/affected]}`, for a project without Graphify (Acceptance 3).

### Implementation for User Story 3

- [ ] T018 [P] [US3] Create `registry/adapters/graphify.yaml` in the form of `registry/adapters/codegraph.yaml`, with the values from contracts/cli.md § Registry entries:
  - `source: graphify`;
  - upstream `https://github.com/Graphify-Labs/graphify`;
  - `license: MIT`, after checking the upstream LICENSE; if it is a different license, use that one;
  - `tested_version: 0.9.72`;
  - `summary` stating that it misses calls made through a module name;
  - install `cli: "uv tool install graphifyy"` and `project-init: "graphify extract . --code-only"`;
  - `available_cmd: graphify`;
  - `portability: [claude-code, codex, cursor, copilot, gemini]`;
  - tools `query` (phases `[research]`), `affected` (`[plan, review]`) and `update` (`[verify]`), all `kind: tool` with `requires: ["project:graphify-out"]` and English triggers.
- [ ] T019 [P] [US3] Create `registry/adapters/open-skill-cli.yaml` with `available_cmd: open-skill`, this repository as upstream, its license, and one tool:
  - `name: session-update`, `kind: tool`, `invoke: "open-skill session update"`;
  - `phases: [review, verify]`, `requires: ["project:graphify-out"]`;
  - triggers `["other session", "which session", "session conflict", "parallel session"]` and `triggers_i18n: {vi: [session khác, đụng session]}` (R9).
- [ ] T020 [US3] In `spec/taxonomy.yaml`, add `graphify: ["graphify-out"]` under `tool_markers` (line 117). In `cli/open_skill/project.py`, `inspect()` also returns `"graphify"`, computed the same way as `"codegraph"`. In `cli/open_skill/route.py:361`, add `"graphify"` to the reported project keys. Make T016 pass.
- [ ] T021 [US3] Add a row to the table in `skills/open-skill-intel/SKILL.md` after line 15: "Which other session my change affects | Graphify, when `graphify-out/` exists | `open-skill session update --session <id> --json`". Add one sentence: inside a declared session, filter Graphify answers to the session's scope, and keep codegraph for call-level questions. Run `.venv/bin/open-skill lint skills/`.
- [ ] T022 [US3] Run `.venv/bin/open-skill validate` and `.venv/bin/open-skill eval`, and tune the triggers in T018/T019 until the three T017 cases pass and no existing case regresses (SC-005). If a fixture registry test needs it, mirror the adapters in `tests/fixtures/repo/registry/adapters/`.

**Checkpoint**: evals are green; all three stories work.

---

## Phase 6: Polish & cross-cutting

- [ ] T023 [P] Add a "Parallel sessions" section to `README.md` after "## See and question the graph" (line 101): install Graphify, `graphify extract . --code-only` once, then `session start`/`update`/`list`/`end`, and the limit that Graphify misses calls made through a module name, so codegraph stays. Update line 27 to "18 adapters".
- [ ] T024 [P] Mirror T023 in `README.vi.md`, in Vietnamese, with the same structure and position (`tests/test_docs.py` checks the READMEs match).
- [ ] T025 [P] Under `## [Unreleased]` in `CHANGELOG.md`, add an `### Added` list:
  - `open-skill session start|list|end|update`;
  - the adapters `graphify` and `open-skill-cli`;
  - `project.inspect` reporting `graphify`.
  Add a `### Changed` entry: the lock helper moved to `paths.locked`.
- [ ] T026 Run `.venv/bin/open-skill build` to regenerate playbooks, schemas and `dist/`, then `.venv/bin/open-skill build --check`.
- [ ] T027 Run every quality gate from the constitution:
  - `.venv/bin/pytest -q`;
  - `.venv/bin/open-skill eval`;
  - `.venv/bin/open-skill validate`;
  - `.venv/bin/open-skill lint skills/`;
  - `.venv/bin/open-skill build --check`;
  - `.venv/bin/python scripts/privacy_guard.py`.
- [ ] T028 Run quickstart.md end to end against real Graphify 0.9.72 on a scratch copy, and record in the PR description:
  - SC-001: the `time` result;
  - SC-003: the 20-run concurrency loop, with no `bad graph` line;
  - the four error-path rows.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (T001–T002)**: none; the two tasks can run in parallel.
- **Foundational (T003–T005)**: T003 before T005, because T005 uses `paths.locked`. T004 can be written in parallel with T003. This phase blocks US1 and US2.
- **US1 (T006–T012)**: needs Foundational, T001 and T002.
- **US2 (T013–T015)**: needs Foundational only. It can run in parallel with US1, but both edit `cli.py` and `sessions.py`, so run them one after the other when working alone.
- **US3 (T016–T022)**: independent of US1 and US2 in code. T017's `session-update` case only needs the adapter YAML (T019), not the command.
- **Polish (T023–T028)**: after the stories you ship. T026 comes after T018 and T019; T027 and T028 come last.

### User story dependencies

- **US1 (P1)**: uses the record store from Foundational, not US2's CLI.
- **US2 (P2)**: independent of US1.
- **US3 (P3)**: independent. Routing to `open-skill session update` is only useful once US1 ships.

### Within each story

Tests, then walk and helpers, then the CLI wiring. Tests must fail before the code is written.

## Parallel Example: User Story 1

```text
T006 walk tests  ─┐
T007 git tests   ─┼─ same file tests/test_session_update.py: write together, one editor
T008 CLI tests   ─┘
then T009 → T010 → T011 → T012 (same module, in order)
```

## Parallel Example: User Story 3

```text
T016 tests/test_project.py      ─┐
T017 evals/routing.yaml         ─┤ all different files
T018 registry/adapters/graphify.yaml ─┤
T019 registry/adapters/open-skill-cli.yaml ─┘
then T020 → T021 → T022
```

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 1 and Phase 2.
2. Phase 3 (US1): `session update` works with sessions made through the API or by hand-written records.
3. Stop and validate: run quickstart.md § End-to-end, creating the records with `.venv/bin/python -c "from open_skill import sessions; ..."`.

### Incremental delivery

1. MVP (US1): conflict warnings work.
2. Add US2: sessions can be managed from the CLI; this is the first version for users.
3. Add US3: the router and intel skill point agents to it.
4. Polish: docs, build and gates, then release.

### Suggested commits

One commit per checkpoint: Foundational, US1, US2, US3, Polish. Each commit message ends with the repository's co-author line.
