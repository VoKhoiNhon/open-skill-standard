# Releasing

Releases follow [Semantic Versioning](https://semver.org/) and the changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Branches are kept after merge.

1. **Branch:** `git checkout -b release/vX.Y.Z` from an up-to-date `main`.
2. **Changelog:** move the `[Unreleased]` entries into a new `## [X.Y.Z] - YYYY-MM-DD` section and update the compare links. Start the section with a one-line theme (`Evaluation: ...` or `Release engineering.`); the release is titled `vX.Y.Z — <theme>` from it.
3. **Version:** `uv run python scripts/bump_version.py X.Y.Z`, then `uv run open-skill build`. This sets the version in `pyproject.toml`, the package, the plugin manifest and the open-skill adapter, and pins every skill to `@vX.Y.Z`. `scripts/check_versions.py` verifies it.
4. **Pull request:** titled `release: vX.Y.Z — <theme>`; merge with a merge commit once CI is green.
5. **Tag:** `git tag -a vX.Y.Z -m vX.Y.Z && git push origin vX.Y.Z`. The `release` workflow checks that the tag matches the package version, builds the wheel and sdist, creates the GitHub release from the CHANGELOG section if it does not exist, and attaches the artifacts.
6. **PyPI (optional):** configure a [trusted publisher](https://docs.pypi.org/trusted-publishers/) on PyPI for this repository, workflow `release.yml` and environment `pypi`, then set the repository variable `PUBLISH_TO_PYPI=true`. No API token is stored.

## What a release must never do

- Change or delete anything in a user's `~/.open-skill/`. Data changes ship as migrations in `cli/open_skill/userdata.py` (with tests that keep note text byte-identical), and seed changes ship as new text under the same seed id.
- Rename a seed id. Retire the old id and add a new one instead.
