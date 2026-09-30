# Research: Parallel sessions on one shared project graph

All findings were checked on 2026-09-30 against Graphify 0.9.72 (`uv tool install graphifyy`) and this repository.

## R1. Command name: `session update`, not `graph update`

- **Decision**: The refresh-and-check command is `open-skill session update [--session ID] [--json]`.
- **Rationale**: `open-skill graph` already exists and exports the *skill* graph (`--format mermaid|json|html`, `cli/open_skill/cli.py:748`). Adding a `graph update` subcommand under it would mix the skill graph with the code graph and turn `graph` into a command with optional subcommands, which argparse handles poorly next to its existing flags. Every other command in this feature lives under `session`.
- **Alternatives considered**: `graph update` with optional argparse subparsers (confusing and fragile with the existing flags); a top-level `code-graph` command (a new top-level name for one action).
- **Spec impact**: spec.md is updated to say `open-skill session update` wherever it said `open-skill graph update`.

## R2. Serializing refreshes: use Graphify's own lock

- **Decision**: open-skill adds no lock around the refresh. It calls `graphify update .`, which already waits on a per-repo lock.
- **Rationale**: in `graphify/cli.py` the `update` command calls `_rebuild_code(..., block_on_lock=True)`. `graphify/watch.py:167` `_rebuild_lock` takes `fcntl.flock` (POSIX) or `msvcrt.locking` (Windows) on `graphify-out/.rebuild.lock`, and it is released if the process dies. The graph is written through `os_replace_with_fallback`, so a reader always sees either the old or the new complete `graph.json`. A second lock in open-skill would add nothing (constitution VII). This also closes the Windows gap for the refresh.
- **Alternatives considered**: an open-skill `.open-skill/graph.lock` (duplicates Graphify's lock and does not cover Graphify's own git hooks, which use Graphify's lock).
- **Spec impact**: FR-008 is met by Graphify. The session-record lock (FR-014) still uses open-skill's lock.

## R3. Session-record lock: generalize `knowledge._locked`

- **Decision**: Move `_locked()` from `knowledge.py:104` to `paths.py` as `locked(path: Path)`. `knowledge.py` calls `locked(home() / ".lock")`, and sessions call `locked(<project>/.open-skill/sessions/.lock)`.
- **Rationale**: one lock helper, already tested by the concurrent-learn fix (commit 6f30ff2). The no-`fcntl` fallback and its `ponytail:` note carry over unchanged.
- **Alternatives considered**: a second copy in `sessions.py` (duplicated code); lock-free writes of one file per session (would work for `start`, but `update` rewrites `seen` while `list --prune` deletes files, so a lock keeps prune from deleting a record being rewritten).

## R4. Shrink refusal and exit codes of `graphify update`

- **Decision**: Treat any non-zero exit of `graphify update .` as a failed refresh: print Graphify's stderr, add the hint `rerun: graphify update . --force`, skip the conflict check and exit 1. open-skill never passes `--force` itself.
- **Rationale**: Graphify exits 0 on success and when nothing changed (checked). It exits 1 with "Nothing to update or rebuild failed" when the rebuild fails or its shrink guard (`watch.py:1221` `_check_shrink`) refuses a write. The guard allows a legitimate shrink (nodes lost only from deleted or re-extracted files), which is why deleting all of `cli/open_skill/*.py` in a scratch copy did not trigger it. It exits 2 on bad arguments.
- **Alternatives considered**: parsing Graphify's messages to tell the cases apart (brittle across versions; the exit code is enough).

## R5. Graph format and the affected-files walk

- **Decision**: Read `graphify-out/graph.json` with `json` (networkx node-link: `nodes[]` with `id` and `source_file`, `links[]` with `source`, `target`, `relation`). Walk edges in reverse (target → source) for up to 2 hops, starting from every node whose `source_file` is a changed file. Follow the relations `calls`, `indirect_call`, `references`, `imports` and `imports_from`. The result is the set of `source_file` values reached, minus the changed files.
- **Rationale**: relation counts on this repo are `contains` 1,733, `calls` 890, `references` 326, `rationale_for` 186, `imports` 168, `imports_from` 162, `indirect_call` 53. Following `imports`/`imports_from` is what catches `tests/test_route.py` (`from open_skill import route`), because Graphify does not resolve `route.target_phase(...)` as a call. `contains` is excluded because it would link every symbol to its file and every file to its package, flagging half the repo.
- **Alternatives considered**: `graphify affected X` per changed symbol (one process of ~130 ms per node, and it fails on ambiguous labels such as `inspect`); codegraph's `affected` (needs a second index and is not what this feature adds).

## R6. Changed files

- **Decision**: `git diff --name-only HEAD` plus `git ls-files --others --exclude-standard`, run in the project root. If `git` fails (not a repo, no commits yet), skip the change and conflict step, print one line and exit 0.
- **Rationale**: this covers staged, unstaged and new files. A repo with no commits makes `HEAD` invalid. That case falls into the same "cannot tell what changed" path rather than a special case.
- **Alternatives considered**: diffing against the graph's manifest (Graphify internals that could change between versions).

## R7. Scope matching and overlap

- **Decision**: A scope is a list of globs relative to the project root, matched with `project._match` (fnmatch, where `*` also crosses `/`, and a leading `**/` also matches at the root). Two sessions overlap when any project file (from `project._files`, same skip list) matches a glob of both. A file is in conflict when it matches a glob of another active session.
- **Rationale**: this reuses the matcher that artifacts and role signals already use, so scopes behave like the rest of open-skill. Comparing globs through real files avoids glob-intersection logic. A glob that matches no file triggers the "matches no file" warning (edge case).
- **Alternatives considered**: `pathlib.PurePath.full_match` (needs Python 3.13; the project supports 3.11); prefix matching only (cannot express `tests/test_route*.py`).

## R8. Session ids and staleness

- **Decision**: ids are `secrets.token_hex(3)` (6 hex characters, for example `a1b2c3`), regenerated on the rare collision. `seen` is an ISO-8601 UTC timestamp. A session is active while `now - seen <= 6 h`. `start`, `update --session` and `end` refresh `seen`; `list` does not.
- **Rationale**: short enough to type or paste into a prompt. `list` must not refresh `seen`, or looking at sessions would keep dead ones alive.
- **Alternatives considered**: reading an agent session id from the environment (not every agent exposes one, constitution I); uuid4 (too long to type).

## R9. Routing entry for the session check

- **Decision**: Add a new adapter `registry/adapters/open-skill-cli.yaml` (`available_cmd: open-skill`) with one tool `session-update` (`invoke: "open-skill session update"`, phases `[review, verify]`, `requires: ["project:graphify-out"]`, triggers such as "other session", "which session", "conflict"). The Graphify adapter describes only Graphify's own commands.
- **Rationale**: tool entries are marked installed per adapter through `available_cmd` (`scan.py:129`). `open-skill.yaml` describes skill folders found by globs, and its `upstream`/`license` fields must stay true (constitution III), so the CLI tool gets its own small adapter.
- **Alternatives considered**: putting `session-update` into `graphify.yaml` (its upstream and license would then describe a command Graphify does not ship); into `open-skill.yaml` (mixes glob-discovered skills with a PATH-detected tool).

## R10. `.open-skill/` inside a project

- **Decision**: Session records live in `<project>/.open-skill/sessions/`. The first `session start` writes `<project>/.open-skill/.gitignore` containing `*`, so records are never committed.
- **Rationale**: session records are machine-local and short-lived (constitution IV). A self-ignoring folder needs no edit to the user's own `.gitignore`. This repository already ignores `/.open-skill/`.
- **Alternatives considered**: storing sessions under `~/.open-skill/projects/<hash>/` (hides them from other tools in the project and makes "which project" ambiguous with worktrees).
