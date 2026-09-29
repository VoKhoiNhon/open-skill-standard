# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `open-skill graph --format html --out graph.html` writes one self-contained page (no network) with skills by phase, artifacts and roles, filters by role, phase, source and installed state, search, keyboard use and a dark theme; `--out` works for every format. Graph JSON nodes now carry skill descriptions and role names.

### Changed
- Releases are titled `vX.Y.Z — <theme>` automatically, from the first line of the CHANGELOG section (`scripts/changelog.py title`).

### Fixed
- Crash and hang reports, in English and Vietnamese ("crashes", "hangs", "bị treo", "văng"), start with debugging instead of a planned build.
- Embedded builds in spec-kit projects use `spec-kit/implement` instead of subagent-driven development.

## [0.5.0] - 2026-09-29

Evaluation: measure how well tasks route to skills and how reliably skills trigger.

### Added
- `open-skill eval routing`: the routing eval runner now lives in the package (`cli/open_skill/evals.py`) and reports results per role.
- Trigger eval sets for the four core skills in `evals/triggers/`, one labeled file per skill.
- `open-skill eval triggers`: a lexical trigger proxy with precision and recall, and CI regression floors so descriptions cannot silently get worse.
- `open-skill eval triggers --agent claude --runs N`: runs each query through Claude Code, detects skill invocations in its stream-json output, counts a query as triggering at a 0.5 trigger rate, and scores a stable 60/40 train/test split.
- Evals ship in the wheel, so both commands work from an installed package.

### Changed
- The open-skill-intel and open-skill-learn descriptions name the questions people actually ask, corrections, forgetting and exports (proxy recall 0.30 → 0.40 and 0.50 → 0.70).
- CI actions updated: checkout v7, setup-uv v7, upload-artifact v7, download-artifact v8.

## [0.4.0] - 2026-09-29

Release engineering.

### Added
- `release` workflow on version tags: verifies the tag matches the package version, builds wheel and sdist, creates the GitHub release from this changelog when missing, and attaches the artifacts.
- Optional PyPI publishing through Trusted Publishing (OIDC), enabled by the `PUBLISH_TO_PYPI` repository variable.
- Checks: Conventional Commits pull request titles, one version everywhere, wheel contents, and an installed-wheel smoke test outside the repository.
- CI on Python 3.11–3.14 and macOS; Dependabot for actions and Python packages.
- `RELEASING.md`, and scripts `bump_version.py`, `check_versions.py`, `changelog.py`, `check_pr_title.py`, `check_wheel.py`.

## [0.3.0] - 2026-09-29

Conformance with the Agent Skills specification, and skill health.

### Added
- Lint rules from the [Agent Skills specification](https://agentskills.io/specification): name characters and hyphens, name matches its folder, `compatibility`, `metadata`, `allowed-tools` and `license` checks, missing referenced files, fields no agent reads, instructions over ~5000 tokens.
- Error and warning severities; `lint --strict` and `lint --format json`.
- Claude plugin manifest lint: `marketplace.json` required fields, source escapes, official-name imitation; `plugin.json` name, version, description.
- `lint --installed` health report by source; `doctor` shows it in one line.

### Changed
- Only errors make `lint` fail by default. CI also lints `.claude-plugin/`.
- SPEC §7 refers to the Agent Skills specification.

## [0.2.0] - 2026-09-29

Safe upgrades: pulling a new release never damages your notes or starter knowledge.

### Added
- Versioned user layer (`~/.open-skill/VERSION`) with a guard that stops an older CLI from writing newer data.
- Atomic writes for notes and profiles.
- `open-skill backup [--list]` and `open-skill restore <zip>` (the current state is backed up first; unsafe archive paths are rejected).
- Migrations with dry run and automatic pre-migration backup; v0 → v1 records seed provenance without changing note text.
- Stable seed ids for all 28 role packs; `open-skill seeds sync` adds new seeds, updates untouched ones, keeps edited ones and never re-creates forgotten ones.
- Review of upstream changes to edited seeds: `seeds diff`, `seeds accept`, `seeds keep`.
- `open-skill upgrade [--dry-run] [--rollback]` and `open-skill status [--json]`.
- Upgrade guarantees in the specification (§5.1).

### Changed
- `init` seeds knowledge through seed sync; `doctor` points to pending upgrades and reviews.

### Fixed
- Backup names sort in creation order; retired seeds are reported once.
- The privacy filter no longer mistakes `package@version` pins for email addresses.

## [0.1.0] - 2026-09-29

First public release: taxonomy and schemas, registry (14 adapters, 28 role packs, 9 model profiles), `open-skill` CLI, four core skills, local knowledge layer, CI with routing evals and privacy guard.

[Unreleased]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/VoKhoiNhon/open-skill-standard/releases/tag/v0.1.0
