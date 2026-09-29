# Contributing

Thanks for helping make skill routing better for everyone. The most useful contributions are data: adapters, role packs and model profiles.

## Setup

```bash
git clone https://github.com/VoKhoiNhon/open-skill-standard && cd open-skill-standard
uv sync
uv run pytest -q
```

Before opening a pull request, all of these must pass (CI runs the same):

```bash
uv run pytest -q                      # unit tests + routing evals for every role
uv run open-skill validate            # schemas and cross-references
uv run open-skill lint skills/ .claude-plugin/   # Agent Skills spec, prompting rules, plugin manifests
uv run open-skill audit skills/ .claude-plugin/ --strict   # heuristic security review of our own skills
uv run open-skill build --check       # generated playbooks/schemas/dist are current
uv run python scripts/privacy_guard.py
```

If `build --check` fails, run `uv run open-skill build` and commit the result.

## Add or update an adapter

1. Clone the upstream project and draft the adapter from its skill folders:
   `uv run open-skill adapter draft --source <name> --from <checkout>/skills > registry/adapters/<name>.yaml`
2. Fill in `upstream`, `license`, `install` (copy commands **verbatim** from the upstream README) and `detect` rules.
3. For each skill, set `phases`, `produces`/`consumes`, `task_size`, `requires`, `conflicts` and role weights where the skill is role-specific. Write descriptions in your own words; never paste upstream skill content.
4. `uv run open-skill adapter check --source <name> --from <checkout>/skills` must report no drift.

## Add or update a role pack

Run `uv run open-skill eval routing` to see pass rates per role before and after your change.

Edit `registry/roles/<role-id>.yaml`: `risk`, 3–5 `constitution` principles, `signals`, per-phase `primary`/`alternatives`, generic `seeds`, and `build_window` if the role does not follow plan → build → verify → review. Add a case to `evals/routing.yaml` showing the behavior you expect. New role ids go into `spec/taxonomy.yaml` first.

Role packs and seeds must stay generic: no company, product or person names, and no internal data.

## Add or update a model profile

When Anthropic publishes a model-specific prompting guide, add `registry/models/<model-id>.yaml` with `match` globs, `inherits` (the previous model of the family), `source` (the guide URL), `verified` (today's date), and only the differences: `traits`, `effort`, `chain.max_steps`, short `addenda` written in your own words, `avoid`. Use `verified: false` when you have not read a dedicated guide.

## Writing skills

Skills in `skills/` must pass `open-skill lint`. Keep them model-neutral: say why instead of shouting MUST/NEVER, keep instructions brief, name the scope, never ask the model to reproduce its reasoning in the reply, and never hard-code a model id.

## Releases

See [RELEASING.md](RELEASING.md).

## Commits and pull requests

Use Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `ci:`). Keep each pull request to one purpose. Larger features follow the repository's own spec-driven flow in `specs/`.

By contributing you agree that your contribution is licensed under the MIT License.
