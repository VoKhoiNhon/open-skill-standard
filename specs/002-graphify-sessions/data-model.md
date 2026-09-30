# Data model: Parallel sessions on one shared project graph

## Session record

One JSON file per session: `<project>/.open-skill/sessions/<id>.json`.

| Field | Type | Rules |
|---|---|---|
| `id` | string | 6 lowercase hex characters, equal to the file name without `.json` (R8) |
| `scope` | list of strings | at least one glob, relative to the project root, forward slashes, no `..` and not absolute |
| `task` | string | 1–200 characters; one line (newlines replaced by spaces) |
| `started` | string | ISO-8601 UTC, set once at `start` |
| `seen` | string | ISO-8601 UTC, refreshed by `start`, `update --session` and `end` (FR-012) |
| `base` | string or null | full commit sha from `git rev-parse HEAD` at `start`; `null` without git or before the first commit (R6) |

Example:

```json
{"id": "a1b2c3", "scope": ["cli/open_skill/route.py"], "task": "speed up fit",
 "started": "2026-09-30T08:00:00Z", "seen": "2026-09-30T08:41:10Z",
 "base": "1859993c0ffee…"}
```

**Validation on read**: a file that is not valid JSON, lacks a field, or whose `id` differs from its file name is *unreadable*. It is skipped by every command and removed by `list --prune`.

### States

```
start ──▶ active ──(no activity > 6 h)──▶ stale ──(list --prune)──▶ removed
             │
             └──(end)──▶ removed
```

- **active**: `now - seen <= 6 h`. It counts for overlap warnings and conflicts.
- **stale**: kept on disk, ignored everywhere, deleted by `--prune`. A later `update --session <id>` on a stale id warns (edge case) and does not revive it.
- `end` deletes the file. There is no "ended" state to keep.

Other files in the folder:
- `.lock`, used by the lock helper (R3);
- `../.gitignore`, containing `*`, written once (R10).

## Shared graph (read-only for open-skill)

`<project>/graphify-out/graph.json`, written only by Graphify.

open-skill reads only:
- `nodes[].id`
- `nodes[].source_file`
- `links[].source`, `links[].target`, `links[].relation`, `links[].source_file`, `links[].source_location`

For each `imports_from` link into a package `__init__.py`, open-skill also reads the one import statement at `source_location` in the importing file, to resolve package imports (R5).

Nodes with an empty `source_file` (external symbols such as `Path`) are ignored.

## Refresh result

Returned by `session update`, printed as text or with `--json` (see [contracts/cli.md](contracts/cli.md)).

| Field | Type | Meaning |
|---|---|---|
| `session` | string or null | the `--session` id, when given and active |
| `graph` | object | `{"refreshed": bool, "nodes": int, "edges": int}` |
| `base` | string or null | the commit changes were compared with: the session's `base`, else `HEAD` (R6) |
| `changed` | list of paths | files differing from `base`, plus untracked files (R6); empty with `git: false` when git is unavailable |
| `git` | bool | whether changed files could be determined |
| `affected` | list of paths | files reached within 2 reverse hops, excluding `changed` (R5) |
| `conflicts` | list of objects | `{"file", "session", "task", "via"}`: an affected (or changed) file inside another active session's scope, and the changed file that reaches it |
| `others` | list of objects | `{"file", "session", "task"}`: with an active `--session`, a changed file that lies only in other sessions' scopes (not in this one's), taken as their work: not walked and not a conflict (N1, option b) |
| `warnings` | list of strings | unknown or stale session id, and similar |

A changed file of this session (in its own scope, or in no session's scope) that also lies inside another session's scope is a conflict, with `via` equal to the file itself. Without `--session`, every changed file counts as this run's change.
