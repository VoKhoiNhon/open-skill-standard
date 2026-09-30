# Quickstart: validate parallel sessions

## Automated (no Graphify needed)

```bash
.venv/bin/pytest tests/test_sessions.py tests/test_session_update.py -q
.venv/bin/open-skill eval
```

Expected results:
- **Tests**: all pass. They put a fake `graphify` script on `PATH` and use the fixture graph `tests/fixtures/graphify/graph.json`. That fixture reproduces Graphify's real package-import shape: a test file reaches the changed module only through `from pkg import (route,)`, which Graphify links to `pkg/__init__.py` (SC-002, R5).
- **Evals**: the routing evals keep their pass rate, plus the new session cases (SC-005).

## End-to-end on this repository (real Graphify)

Prerequisite: `uv tool install graphifyy`. Work on a scratch copy so the checkout stays clean:

```bash
rsync -a --exclude .venv ./ /tmp/oss-e2e/ && cd /tmp/oss-e2e
graphify extract . --code-only
A=$(open-skill session start --scope "cli/open_skill/route.py" --task "speed up fit" | head -1)
B=$(open-skill session start --scope "tests/**" --task "add fixtures for route tests" | head -1)
printf '\n# touch\n' >> cli/open_skill/route.py
time open-skill session update --session "$A"
```

Expected output of the last command:
- it finishes in under 5 s (SC-001);
- it lists `tests/test_route.py` as affected;
- it prints a ⚠ line naming session `$B`;
- its exit code is 0;
- after `git commit -qam touch` and running the same command again, the result is the same (R6).

## Concurrency (SC-003)

```bash
for i in $(seq 20); do open-skill session update & open-skill session update; wait; \
  python3 -c "import json;json.load(open('graphify-out/graph.json'))" || echo "run $i: bad graph"; done
```

Expected: no `bad graph` line.

## Error paths

| Setup | Command | Expected |
|---|---|---|
| `PATH` without graphify | `open-skill session update` | exit 2 + install hint |
| delete `graphify-out/` | `open-skill session update` | exit 2 + `graphify extract . --code-only` hint |
| `rm -rf .git` | `open-skill session update` | exit 0 + "conflict check skipped" note |
| write `{bad` into a session file | `open-skill session list --prune` | `pruned 1 record(s)` |
