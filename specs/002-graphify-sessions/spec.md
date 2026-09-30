# Feature Specification: Parallel sessions on one shared project graph

**Feature Branch**: `002-graphify-sessions`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Graphify-backed parallel session management for open-skill (approach A: one shared graph + per-session scopes). Add a graphify adapter alongside codegraph; sessions with scope and task; `open-skill session update` refreshes the shared graph and warns (never blocks) when a change affects another active session's scope. Out of scope: sharded extraction, daemon/lock server, web UI, automatic scope claiming."

## Context

A user often runs several agent sessions in parallel on one project (for example one session on the router, one on its tests). Each session needs an up-to-date code graph, and each needs to know when its change reaches code another session is working on.

Measurements on this repository (93 code files, ~11k lines of Python, 2026-09-30):

- Refreshing the Graphify graph after a one-file change takes ~2.4 s; a full build takes ~8 s.
- Building one partial graph per folder and merging them with Graphify's own merge loses every relationship that crosses folders: 1,314 nodes / 2,528 edges merged versus 2,204 nodes / 3,566 edges for the whole project. Per-session partial graphs therefore give wrong answers, so all sessions share one graph.
- Graphify misses calls made through a module name (`route.target_phase(...)`), so it reported none of the 6–15 test call sites per function that codegraph found. It also points `from open_skill import route` at the package (`__init__.py`), not at `route.py`: the real graph has 0 edges from `tests/test_route.py` to `route.py`. Impact detection must therefore resolve package imports to the imported module (measured: 7 of 7 direct importers of `route.py` found, versus 4 without).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Refresh the shared graph and see who my change affects (Priority: P1)

A developer finishes an edit in session A and runs one command. The shared project graph is brought up to date, and the command lists the files the change affects. It also warns about any affected file that lies inside another active session's declared scope, naming that session and its task.

**Why this priority**: This is the core value: parallel sessions learn about collisions from the graph while they still can act, instead of at merge time.

**Independent Test**: In a fixture project with a prepared graph and two declared sessions, change a file owned by session A that session B's test file imports, run the refresh for A, and check that B's file is reported as a conflict.

**Acceptance Scenarios**:

1. **Given** sessions A (scope `cli/open_skill/route.py`) and B (scope `tests/**`) are active and `route.py` changed, **When** the user runs `open-skill session update --session A`, **Then** the graph is refreshed and the output warns that `tests/test_route.py` (session B, with its task) is affected.
2. **Given** a test file reaches the changed module only through a package import (`from open_skill import route`), **When** the refresh runs, **Then** that test file is still reported as affected.
3. **Given** session A committed its change to `route.py` before running the refresh, **When** the user runs `open-skill session update --session A`, **Then** `route.py` is still listed as changed and the same conflicts are reported as before the commit.
4. **Given** no other session's scope is affected, **When** the refresh runs, **Then** it reports the affected files and says there are no conflicts.
5. **Given** `--json` is passed, **When** the refresh runs, **Then** the output is one JSON object listing changed files, affected files and conflicts, so an agent can act on it.
6. **Given** two sessions start a refresh at the same moment, **When** both run, **Then** the refreshes run one after the other and the graph is never written by both at once.

---

### User Story 2 - Declare, list and end sessions (Priority: P2)

A developer starts a session with the paths it will work on and a short task, gets an id back, lists the active sessions of the project, and ends a session when done. Starting a session whose scope overlaps an active session's scope prints a warning.

**Why this priority**: Conflict warnings need declared scopes; on its own this story already gives a shared view of who works where.

**Independent Test**: Start two sessions with overlapping scopes in a fixture project, list them, end one, list again.

**Acceptance Scenarios**:

1. **Given** no sessions, **When** the user runs `open-skill session start --scope "cli/**" --task "speed up fit"`, **Then** a session id is printed and the session appears in `open-skill session list` with its scope and task.
2. **Given** an active session with scope `cli/**`, **When** another session starts with scope `cli/open_skill/route.py`, **Then** the start succeeds and warns about the overlap, naming the other session.
3. **Given** a session had no activity for more than 6 hours, **When** sessions are listed or checked for conflicts, **Then** it is treated as ended and does not trigger warnings.
4. **Given** stale or unreadable session records, **When** the user runs `open-skill session list --prune`, **Then** those records are removed and the others kept.
5. **Given** an active session, **When** the user runs `open-skill session end <id>`, **Then** it no longer appears in the list.

---

### User Story 3 - The router and intel skill know about Graphify (Priority: P3)

In a project that has a Graphify graph, the router can place Graphify's query, affected and update tools in a route, and `open-skill-intel` tells the agent to scope graph questions to its session. Codegraph stays available and keeps its place for call-level questions.

**Why this priority**: It makes the feature reachable through the normal routing flow; the commands work without it.

**Independent Test**: Run the routing evals with a project that has a Graphify graph and check the new cases pass without breaking existing ones.

**Acceptance Scenarios**:

1. **Given** a project containing Graphify output, **When** the project is inspected, **Then** Graphify is reported as present, the same way codegraph is.
2. **Given** a task such as "which other session does my change affect", **When** it is routed in that project, **Then** the route includes the session conflict check.
3. **Given** a project without Graphify output, **When** tasks are routed, **Then** Graphify tools are not placed in the route and existing routes are unchanged.

### Edge Cases

- Graphify is not installed: the command exits with code 2 and prints the install command taken from the adapter.
- The project has no graph yet: the command says so and suggests the first full build command; it does not start a build itself.
- Graphify refuses to replace the graph with a smaller one (after a large deletion): its message is passed on with the hint to rerun with force; open-skill never forces on its own.
- The project is not a git repository: the graph is refreshed, the change-and-conflict step is skipped, and one line explains why.
- The session's start commit no longer exists (history rewritten and cleaned up): changes are compared with the current commit instead, with a warning naming the missing commit.
- Other sessions share the working tree, so their edits since the start commit also count as changes: the check over-reports rather than misses.
- A session record is corrupt or unreadable: it is ignored everywhere and removed by `--prune`.
- The session id given to `session update` does not exist or is stale: the refresh still runs, conflicts are computed against all active sessions, and a warning names the unknown id.
- A scope glob matches no file: the session is still created, with a warning.
- On Windows, where the file lock used today is unavailable, session-record writes run without a lock, as the knowledge store already does; this limit is documented. Graph refreshes stay serialized by Graphify's own lock on every platform.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The registry MUST include a Graphify adapter describing its query, affected and update tools with phases, triggers, install command and upstream link, in the same form as the codegraph adapter. The codegraph adapter MUST NOT change.
- **FR-002**: Project inspection MUST report whether a project has Graphify output, alongside the existing codegraph flag.
- **FR-003**: Users MUST be able to start a session with one or more scope globs and a task, and receive a session id.
- **FR-004**: Session records MUST live inside the project (under `.open-skill/sessions/`), one record per session, holding id, scope, task, start time, last activity time and the commit the project was at when the session started (none without git).
- **FR-005**: Users MUST be able to list active sessions and end a session; listing with `--prune` MUST remove stale and unreadable records.
- **FR-006**: A session with no activity for more than 6 hours MUST be treated as ended by every command.
- **FR-007**: Starting a session whose scope overlaps an active session's scope MUST warn and MUST still create the session.
- **FR-008**: `open-skill session update` MUST refresh the project's Graphify graph incrementally, with only one refresh per project running at a time.
- **FR-009**: After refreshing, the command MUST determine the changed files, meaning every file that differs from the session's start commit (committed, staged, unstaged or untracked; the current commit when no session is named), and the files affected by them within two steps of calls, references or imports in the graph, where an import of a package counts as an import of each module it names.
- **FR-010**: The command MUST warn, and never block or fail, when an affected file falls inside another active session's scope, naming that session and its task.
- **FR-011**: The command MUST offer a machine-readable output with changed files, affected files and conflicts.
- **FR-012**: Every command that names a session MUST update that session's last activity time.
- **FR-013**: The error cases listed under Edge Cases MUST behave as described, with exit code 2 for a missing Graphify install and no automatic full builds or forced writes.
- **FR-014**: Concurrent writes to one session record MUST never lose data: two sessions started at the same moment both end up recorded.
- **FR-015**: Routing evals MUST gain cases for session-conflict tasks, and README (English and Vietnamese) and CHANGELOG MUST document the feature.

### Key Entities

- **Session**: one agent working session in a project. Id, scope (list of path globs relative to the project root), task (short text), started, last seen. Active while last seen is within 6 hours.
- **Shared graph**: the single Graphify graph of the project, refreshed in place by any session.
- **Refresh result**: changed files, affected files, and conflicts (affected file, owning session, its task, the changed file that reaches it).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On this repository, a refresh after a one-file change, including the conflict check, completes in under 5 seconds.
- **SC-002**: In the fixture scenarios, 100% of files that call or import a changed file within two steps are reported as affected, including test files that reach the module only through a package import; and on this repository, every file that imports `route.py` directly, by module or through the package, is reported when `route.py` changes.
- **SC-003**: Two refreshes started at the same moment always finish with a valid graph, in 20 out of 20 repeated runs.
- **SC-004**: No command in this feature ever blocks a user's edit or exits with an error because of a conflict.
- **SC-005**: Existing routing evals for all 28 roles keep their current pass rate, and every quality gate in the constitution passes.

## Assumptions

- Users install Graphify themselves (`uv tool install graphifyy`) and build the first graph themselves; open-skill only refreshes it, in line with "indexing is the user's decision".
- Code-only graphs are enough; document extraction through an LLM is out of scope.
- Sessions on one project share one working tree. Sessions in separate git worktrees each have their own graph and are out of scope.
- The 6-hour stale window is a fixed value; making it configurable waits for a real need (constitution VII).
- Scopes are declared by the user or agent; automatic scope claiming, sharded extraction, a lock server or daemon, and a web view are out of scope.
- Serialized writes reuse the existing knowledge-store lock, extended to take a lock path, instead of a second locking mechanism (constitution VII).
- Codegraph stays the primary tool for call-level questions because it resolves calls through module names, which Graphify misses.
