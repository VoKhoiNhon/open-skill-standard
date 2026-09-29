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
uv run python scripts/render_assets.py --check   # README images match the code and registry
```

If `build --check` fails, run `uv run open-skill build` and commit the result. If `render_assets.py --check` fails, run `uv run python scripts/render_assets.py` and commit the images it rewrites in `.github/assets/`.

## Add or update an adapter

1. Clone the upstream project and draft the adapter from its skill folders:
   `uv run open-skill adapter draft --source <name> --from <checkout>/skills > registry/adapters/<name>.yaml`
2. Fill in `upstream`, `license`, `install` (copy commands **verbatim** from the upstream README) and `detect` rules.
3. For each skill, set `phases`, `produces`/`consumes`, `task_size`, `requires`, `conflicts` and role weights where the skill is role-specific. Write descriptions in your own words; never paste upstream skill content.
4. `uv run open-skill adapter check --source <name> --from <checkout>/skills` must report no drift.

## Add or update an agent target

Agent targets (`registry/agents/<id>.yaml`, SPEC §4.6) say where a coding agent loads skills. Take every path from the agent's official documentation; when the docs are silent (how to tell the agent is installed, an env var that moves its home), take it from the source of [vercel-labs/skills](https://github.com/vercel-labs/skills/blob/main/src/agents.ts), linking a pinned commit and line. Put the URL in the `source` of each path, list the install target first, and never guess a path. Use the same id as the skills CLI where one exists. Update the agent tables in both READMEs; a test checks them.

## Add or update a role pack

Run `uv run open-skill eval routing` to see pass rates per role before and after your change. It also prints the score on `evals/routing-holdout.yaml`, requests that routing was never tuned on. Tune against `evals/routing.yaml` (which must stay at 100%), never against single holdout cases, and do not relabel a holdout case to match the router. Put the holdout score before and after in the pull request; CI only enforces a floor just below it (`HOLDOUT_ROUTING_FLOOR` in `tests/test_evals.py`), which you raise when the score goes up.

Edit `registry/roles/<role-id>.yaml`: `risk`, 3–5 `constitution` principles, `signals`, per-phase `primary`/`alternatives`, generic `seeds`, and `build_window` if the role does not follow plan → build → verify → review. Add a case to `evals/routing.yaml` showing the behavior you expect. A test keeps every role at 5 or more cases across 3 or more phases and every primary placed by some case, so a new primary needs a case that places it. New role ids go into `spec/taxonomy.yaml` first.

Role packs and seeds must stay generic: no company, product or person names, and no internal data.

## Add or update a model profile

When Anthropic publishes a model-specific prompting guide, add `registry/models/<model-id>.yaml` with `match` globs, `inherits` (the previous model of the family), `source` (the guide URL), `verified` (today's date), and only the differences: `traits`, `effort`, `chain.max_steps`, short `addenda` written in your own words, `avoid`. Use `verified: false` when you have not read a dedicated guide.

## Writing skills

Skills in `skills/` must pass `open-skill lint`. Keep them model-neutral: say why instead of shouting MUST/NEVER, keep instructions brief, name the scope, never ask the model to reproduce its reasoning in the reply, and never hard-code a model id.

A skill's `description` decides when agents load it. To change one, run `uv run open-skill eval triggers --suggest` before and after, tune against the failures it lists (tuning queries only), and never against queries marked `holdout: true`. Look for the concept a group of misses shares instead of pasting their words in. Put the before and after holdout precision and recall in the commit message, and raise the per-skill floors in `tests/test_evals.py` when scores go up.

Descriptions are English only. Queries in another language carry `locale: <tag>` and are reported as a slice per language (floors in `LOCALE_FLOORS`); for them the proxy also reads each skill's `triggers_i18n` for that language, since it cannot translate. When a slice drops, improve the English wording or the locale block in the registry, never the description with words in that language.

## Documentation languages

English is the project's language: README.md, the SPEC, skills, CLI output, comments and test names. `README.vi.md` is a Vietnamese translation of README.md. When you change a section, a command or an example output in README.md, change it in README.vi.md too (in English if you do not write Vietnamese; a reviewer can translate the prose). A test checks that both have the same headings and the same command and output blocks.

## Releases

See [RELEASING.md](RELEASING.md).

## Commits and pull requests

Use Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `ci:`). Keep each pull request to one purpose. Larger features follow the repository's own spec-driven flow in `specs/`.

By contributing you agree that your contribution is licensed under the MIT License.
