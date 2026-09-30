# CLI contract: `open-skill session`

Every subcommand takes `--project PATH`; the default is the current directory. Exit codes follow `cli.py`:
- `0` ok (warnings included);
- `1` environment failure (Graphify refresh failed, folder not writable);
- `2` bad input or a missing prerequisite.

Conflicts never change the exit code (FR-010, SC-004).

## `session start --scope GLOB [--scope GLOB ...] --task TEXT [--project PATH] [--json]`

Creates a session record, with `base` set to the current commit, and prints its id on stdout: text mode prints the id alone on the first line; `--json` prints the full record.

Warnings go to stderr, one line each:

```
warning: scope overlaps session b4c5d6 ("add fixtures for route tests"): tests/test_route.py
warning: scope glob matches no file: docs/new/**
```

Overlap is judged on the project's listed files (generated folders skipped, first 5,000 files), and an identical glob in both scopes always overlaps (research R7).

The command exits 2 when:
- no `--scope` is given;
- a glob is absolute or contains `..`;
- the task is empty.

## `session list [--project PATH] [--json] [--prune]`

Text mode prints one line per active session, newest `seen` first:

```
a1b2c3  seen 12m ago  cli/open_skill/route.py        speed up fit
b4c5d6  seen 3m ago   tests/**                       add fixtures for route tests
```

`--json` prints a list of session records.

`--prune` first deletes stale and unreadable records, then prints to stderr `pruned N record(s)`. `list` never refreshes `seen`.

## `session end ID [--project PATH]`

Deletes the record. It exits 2 with `open-skill: no such session: ID` when the id is unknown. Ending a stale session also works.

## `session update [--session ID] [--project PATH] [--json]`

Steps and what the user sees:

1. **Prerequisites.**
   - `graphify` not on PATH → exit 2, stderr: `open-skill: graphify is not installed; install it with: uv tool install graphifyy`. The install command is read from the Graphify adapter.
   - No `graphify-out/graph.json` → exit 2, stderr: `open-skill: no graph yet; build it once with: graphify extract . --code-only`.
2. **Refresh.** Runs `graphify update .` in the project root and waits on Graphify's own lock (R2). If it exits non-zero, open-skill passes Graphify's stderr through, adds `hint: if code was deleted on purpose, rerun: graphify update . --force`, and exits 1.
3. **Changes.** Reads the files that differ from the base commit (R6): the session's `base` with `--session`, else `HEAD`. If the base commit is gone, it falls back to `HEAD` with the warning `session base <sha> is gone; compared with HEAD`. If git is unavailable, prints `note: not a git repository (or no commits); conflict check skipped` and exits 0 after reporting the refresh.
4. **Impact.** Computes the files affected by the changes, including package imports resolved to modules (R5), and the conflicts with other active sessions (R7). The session given with `--session` is excluded from conflicts. With an active `--session`, a changed file that lies only in other sessions' scopes is listed under `others` as their work, and is neither walked nor a conflict.
5. **Activity.** If `--session` is active, refreshes its `seen`. If the id is unknown or stale, adds the warning `session ID is unknown or stale; checked against all active sessions`.

Text output:

```
graph: 2204 nodes, 3566 edges (refreshed)
changed: cli/open_skill/route.py
affected: 4 files
  cli/open_skill/cli.py
  cli/open_skill/evals.py
  tests/test_route.py
  tests/test_why_not.py
⚠ tests/test_route.py is in session b4c5d6 ("add fixtures for route tests"), reached from cli/open_skill/route.py
· tests/fixtures/new.yaml changed in session b4c5d6 ("add fixtures for route tests"); counted as its work
```

`--json` prints exactly one object with the fields of *Refresh result* in [data-model.md](../data-model.md), and nothing else on stdout.

## Registry entries

- `registry/adapters/graphify.yaml`:
  - `source: graphify`;
  - upstream `https://github.com/Graphify-Labs/graphify`;
  - `tested_version: 0.9.72`;
  - `available_cmd: graphify`;
  - install `uv tool install graphifyy`;
  - project-init `graphify extract . --code-only`;
  - tools `query` (research), `affected` (plan, review) and `update` (verify), all with `requires: ["project:graphify-out"]`.
- `registry/adapters/open-skill-cli.yaml`: `available_cmd: open-skill` and one tool `session-update` (R9).
- `spec/taxonomy.yaml` `tool_markers`: `graphify: ["graphify-out"]`. `project.inspect` returns `graphify: bool` next to `codegraph`, and `route.py:361` includes it in the reported project.
