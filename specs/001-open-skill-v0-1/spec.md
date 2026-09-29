# Feature Specification: Open Skill Standard v0.1

**Created**: 2026-09-29 · **Status**: Implemented

## User Scenarios

1. **Route a task (P1).** A user in any project asks for a change; the router returns an ordered chain of installed skills with reasons, runs step 1, and records what ran.
   *Acceptance:* In a spec-kit project a large build task starts at `speckit-specify` (or `speckit-plan` when a spec exists) and never mixes in another build workflow.
2. **Work in any IT role (P1).** A user in one of 28 roles gets a chain shaped for that role; an analyst gets analyze → validate → visualize, not plan → build.
   *Acceptance:* Every role has at least one routing eval that passes.
3. **Learn the user (P2).** Lessons and preferences the user saves appear in later routes; accepted and replaced skills shift rankings.
   *Acceptance:* Feedback flips a close ranking; notes are attached by scope.
4. **Survive model changes (P2).** An unknown model routes with its family's profile or the generic one; weekly automation reports models that lack a profile.
5. **Stay current with upstream (P3).** Drift between adapters and upstream repositories is detected weekly.

## Functional Requirements

- FR-001 Registry documents validate against schemas generated from the taxonomy.
- FR-002 Installed skills are discovered through adapter detect rules; local skills without a manifest are harvested with inferred metadata and need two words in common with the task to be chosen.
- FR-003 Routing honors native frameworks, conflicts, project requirements, role build windows and model step limits.
- FR-004 User data stays under `~/.open-skill/`; sensitive text is refused; CI blocks user-layer files.
- FR-005 Skills pass the lint rules; generated files are checked in CI.

## Success Criteria

- SC-001 All routing evals pass, covering all 28 roles.
- SC-002 Adapter drift is zero against upstream at release.
- SC-003 Installing on a clean machine takes three commands.
