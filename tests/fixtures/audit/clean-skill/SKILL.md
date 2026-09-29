---
name: clean-skill
description: Formats release notes from merged pull requests. Use when the user asks for release notes or a changelog draft.
---

# Release notes

1. List merged pull requests since the last tag with `git log --merges --oneline <tag>..HEAD`.
2. Group them by Conventional Commit type, using [the guide](references/guide.md).
3. Run `scripts/build.sh` to render `assets/template.txt`, then show the draft to the user for review before saving it.

Ask the user before pushing or tagging anything.
