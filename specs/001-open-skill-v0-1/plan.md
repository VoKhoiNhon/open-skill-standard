# Implementation Plan: Open Skill Standard v0.1

**Technical context:** Python ≥ 3.11, stdlib `sqlite3` (FTS5), PyYAML, jsonschema, pytest, hatchling, uv, GitHub Actions.

## Architecture

- `spec/` — taxonomy (phases, artifacts, edges, sizes, 28 roles, native markers) and JSON Schemas generated from it.
- `registry/` — YAML source of truth: adapters (metadata about upstream skills, never their content), role packs, model profiles.
- `cli/open_skill/` — load and validate the registry, scan installed skills, build an FTS5 index and graph, route tasks, keep the local knowledge layer, lint skills, generate readable playbooks.
- `skills/` — the four core skills agents load: router, standards, intel, learn.
- Layers merge L0 (this registry) → L1 (organization overlays) → L2 (the user's `~/.open-skill/`).

## Constitution Check

I–VII satisfied: agent-neutral schema (I); routing logic in YAML with evals (II); adapters without vendored content (III); local-only user layer with a privacy guard (IV); sourced model profiles with `verified` flags (V); lint for model-neutral skills (VI); no servers (VII).
