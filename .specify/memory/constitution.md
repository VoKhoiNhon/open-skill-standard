# Open Skill Standard Constitution

## Core Principles

### I. Agent-agnostic
The standard describes skills, roles, phases and artifacts without assuming one agent. Claude Code specifics (plugin paths, built-in skills) live in adapters, never in the core schema.

### II. Data over prompts
Selection logic lives in reviewable data (adapters, role packs, model profiles) and a deterministic router, not in long prompts. A behavior change should be a YAML diff with a routing eval that shows it.

### III. Integrate, never vendor
Upstream skills are described as metadata with official install commands. Their content is never copied, their licenses and trademarks are respected, and drift is detected weekly.

### IV. Local-first user data
Profiles, knowledge notes and usage history stay on the user's machine. Nothing personal or organization-specific enters the public registry; organizations use overlays.

### V. Evidence for every claim
Model guidance, install commands and capability statements cite their source. Unverified entries say so (`verified: false`). Tests, evals and the privacy guard gate every change.

### VI. Model-neutral skills
Skills avoid model IDs and patterns current models handle badly; model-specific notes live in model profiles that inherit and fall back to `generic`, so new models never break routing.

### VII. Simplest thing first
Standard library and files before servers and dependencies (SQLite FTS5, not a search cluster). Add complexity only when a measurement shows the need.

## Quality Gates

Every change passes: unit tests, routing evals for every role, `open-skill validate`, `open-skill lint skills/`, `open-skill build --check`, and `scripts/privacy_guard.py`.

## Governance

This constitution guides every spec, plan and review in `specs/`. Amendments are pull requests that update this file, bump the version below, and explain the reason.

**Version**: 1.0.0 | **Ratified**: 2026-09-29 | **Last Amended**: 2026-09-29
