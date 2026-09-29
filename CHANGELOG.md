# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/VoKhoiNhon/open-skill-standard/releases/tag/v0.1.0
