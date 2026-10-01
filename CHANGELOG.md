# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- A GitHub Pages site at https://vokhoinhon.github.io/open-skill-standard/ (English, with a Vietnamese page): a landing page built from the README's diagrams and a live skill graph page, built by `scripts/build_site.py` and deployed by `.github/workflows/pages.yml` on every push to `main`. The build uses a clean home and an empty PATH, so the graph shows the registry and nothing installed on the build machine. The site's install command is version-checked with the READMEs.
- A project logo: a skill graph with one ordered route through it (`.github/assets/logo.svg`, `logo-dark.svg`, and `site/favicon.svg` as the app icon), shown at the top of both READMEs and in the site header.
- The site is redesigned: Geist type, a split hero with the route capture, registry numbers filled in by `scripts/build_site.py` so they cannot drift, a bento of the core parts, sticky steps beside the diagrams, a scrolling role marquee, a closing call to action and a 404 page. Motion (staggered reveals, wipes, count-up, cursor spotlight and tilt) is transform and opacity only, off under prefers-reduced-motion, and the page reads in full without JavaScript.
- The site's build writes `graph.html` when given a relative output folder (as CI does), and fails if the page is missing; the first deploy published no skill graph page.
- `open-skill session start|list|end|update`: parallel agent sessions on one project declare their scope, share one Graphify graph, and get a warning (never an error) when a change reaches another session's scope. Changes count from the session's start commit, so committed work is included; `from pkg import mod` is resolved to `mod.py` because Graphify links it to the package. With `--session`, a changed file that lies only in another session's scope is reported as that session's work (`others`), not as a conflict.
- Adapters `graphify` (query, affected, update; Apache-2.0, tested with 0.9.72) and `open-skill-cli` (`session-update`), and routing evals for session conflicts.
- `project.inspect` and `route` report whether a project has a Graphify graph (`graphify-out/`).
- `python -m open_skill.benchmark` scores the router against baselines and ablations with the same checks as `open-skill eval routing`, on the tuned and held-out cases: description match only (BM25 top-1 over the router's own index), a random skill in the router's phases (expected pass over 200 seeded draws), the router without phase detection and without role priors. It reports 95% Wilson intervals, wins and losses against description match with an exact McNemar test, and route latency; `--json` for machine output.
- The README shows the held-out benchmark as a chart (light and dark), drawn by `scripts/render_assets.py` from the benchmark itself, so CI keeps it current.
- `open-skill audit` flags `remote-exec` (medium): a download piped straight into a shell or interpreter that reads its program from stdin (`curl ... | sh`, `| env bash`, `bash <(curl ...)`, `bash -c "$(curl ...)"`, `iwr ... | iex`, `exec(urlopen(...))`), which runs code nobody read; piping a response into `jq` or `python -m json.tool` is fine.
- `open-skill audit` flags `encoded-exec` (high): text decoded and run as a command (`base64 -d | sh`, `xxd -r | bash`, `eval "$(echo ... | base64 -d)"`, `exec(b64decode(...))`, `powershell -enc`), a way to hide a payload from a reviewer.
- `open-skill audit` flags `exfil-endpoint` (high): request-collection and paste services (webhook.site, RequestBin, Pipedream, interactsh and OAST hosts, Burp Collaborator, canary tokens, the Pastebin API), where stolen data is usually sent. Chat webhooks are left out because notification skills use them openly.
- `open-skill audit` flags `hardcoded-secret` (high): API tokens in their issuers' published shapes (Anthropic, OpenAI, GitHub, AWS, Slack, Google, Stripe, npm, GitLab) and private key headers at the start of a line; AWS's documented example key and placeholder bodies (`xxxxxxxx`, `00000000`, `YOUR...`) are ignored.
- The audit's `hidden-unicode` rule also catches Hangul fillers and runs of variation selectors, which can carry a hidden payload one byte per character; a single selector (emoji, CJK glyph variants) is fine. Excerpts escape these characters and the soft hyphen too; Python counts some of them as printable, so they used to be shown raw. Every new rule's gaps are bounded, so a long line is audited in linear time.
- Agent target `kiro-cli` (Kiro): skills in `~/.kiro/skills` and `.kiro/skills`, detected by `~/.kiro`, so `scan`, `agents` and `install --agent kiro-cli` cover it.
- `open-skill lint` warns about a marketplace without a `description`, a marketplace that lists no plugins, and names Claude Desktop rejects (`org`, `org-provisioned`, `unknown`, or over 128 characters): `marketplace-description`, `marketplace-empty` and `marketplace-desktop`, from the validator messages in the marketplace reference.
- `open-skill lint` checks plugin source objects in `marketplace.json` (`marketplace-source`): a known type (`github`, `url`, `git-subdir`, `npm`, `archive`, `command`) with its required fields, full lowercase commit SHAs, https archives with a 64-hex `sha256`, command sources in printable ASCII with a timeout of 1–600 seconds and mode `copy` or `link`, and `headersHelper` on an archive entry only with `"strict": false`.
- `open-skill lint` checks the values of Claude Code frontmatter fields (`field-claude-code`: `effort`, `context`, `shell` and the three booleans), warns when `description` and `when_to_use` together pass the 1,536 characters Claude Code lists (`listing-length`), and warns about skill folders Claude Code skips (`folder-reserved`: `synced`, `anthropic-skills`).
- Agent targets may set `walk_up` (SPEC §4.6): the agent also reads its project skill folders in every parent folder up to the repository root, stopping at a linked worktree's root. Claude Code, Codex, OpenCode and Amp do, as their docs say, so `scan`, `agents` and routing run from `packages/web` now see the skills in the repository's `.claude/skills` or `.agents/skills`. Skills are still installed in the project folder given.
- `open-skill lint` checks a plugin's `plugin.json` against Claude Code's manifest reference: component paths start with `./`, contain no `..`, exist and are the right kind (`skills` folders, `agents` Markdown files, MCP bundles `.mcpb` or `.dxt`) (`plugin-path`); each `commands` map entry sets exactly one of `source` and `content` (`plugin-command`); `userConfig` options are strict objects with a known `type`, a `title`, a `description` and values of the documented types, and a `default` among the `options` (`plugin-user-config`); and unknown top-level fields, which Claude Code strips, are warned about (`plugin-field`).
- `open-skill audit` flags `agent-config-write` (medium): a skill that writes the agent's user-level instructions or memory (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, a `MEMORY.md`) or its settings (`.claude/settings.json`, `.codex/config.toml`, `.gemini/settings.json`, `.cursor/mcp.json`), with a shell redirect, `tee`, `cp`, `mv`, `sed -i`, PowerShell's `Add-Content`, `Set-Content` or `Out-File`, or an instruction to add text to or update the user's own files. Such text outlives the skill and applies to every later session (memory and context poisoning). Editing a project's own `AGENTS.md` or `CLAUDE.md`, reading any of these files, and setup docs that say what to put in a project's settings are not flagged.

### Changed
- The file lock used by `learn` moved to `paths.locked(path)` so session records share it.
- The Windsurf target also reads `.agents/skills` and `~/.agents/skills`, as Devin Desktop documents, so `scan` lists skills there as seen by Windsurf. Claude Code's folders are left out: Windsurf reads them only when reading Claude Code config is turned on.
- The Codex target also reads `/etc/codex/skills`, the folder for skills an administrator installs for every user.
- The `spec-kit` adapter is tested with 1.0.13 and describes the bundled `github` extension (`specify extension add github`): `github-taskstoissues` is the replacement for `taskstoissues`, which is leaving core; each lists the other as an alternative. Held-out routing is unchanged (35/52).
- The `superpowers` adapter is tested with 6.4.2 (no skill added, renamed or removed since 5.1.0); `executing-plans` now runs the whole plan in the session and reviews it once at the end, and its description says so.
- `open-skill lint` checks marketplace and plugin entry names against the characters Claude Code can install (ASCII letters, digits, `.`, `_`, `-`, starting with a letter or digit), as the current marketplace reference defines them; names like `my+tools` or `công-cụ` passed before, and a non-ASCII marketplace name counts as impersonating an official one.
- `install` refuses, with exit 1, to put a skill named `synced` or `anthropic-skills` into a Claude Code skill folder: Claude Code keeps those names for skills synced from claude.ai and never loads them. Other agents still take them.

### Fixed
- On Windows, `learn` and `session` writes now hold the same lock as on Linux and macOS (`msvcrt` byte lock), so two processes updating one note or one session folder no longer overwrite each other.
- On Windows the CLI no longer crashes at start with `UnicodeDecodeError`: every file it reads or writes (taxonomy, registry, evals, notes, generated files) is opened as UTF-8 instead of the locale code page.
- Output piped on Windows (cp1252) no longer fails with `UnicodeEncodeError` on Vietnamese text or arrows: stdout and stderr are switched to UTF-8.
- `open-skill audit`'s `hidden-comment` rule no longer takes seconds on a line of repeated `<!--` openers (about 10 s for 200 KB): a comment is read up to the next opener.
- `open-skill build` writes generated files (playbooks, schemas, `dist/`) with LF line endings on Windows too; it wrote CRLF there, rewriting every generated file.
- On Windows, `scan`, `lint`, `install`, `adapter check`, the agent memory import and the privacy guard read SKILL.md files, plugin manifests and memory notes as UTF-8; non-ASCII names and descriptions came out garbled, so a skill named `tóm-tắt` failed `name-matches-folder` and imported memory notes were stored mangled.
- On Windows, `scan` (and so `doctor`, `agents`, `search --installed` and routing) matched installed skills against adapter rules with mixed `\` and `/` separators, so every skill in a project folder and every relocated agent home was reported as an unknown harvested skill instead of its registry id; paths are compared in `/` form.
- `scan` (and so `doctor`, `agents` and routing) finds project skills when the project's folder name contains `[`, `]` or `?`, such as `app [v2]`; the folder was read as a glob pattern and every project skill was missed.
- `open-skill lint` no longer warns (`field-claude-code`) about `disable-model-invocation`, `user-invocable` or `background` set to `yes`, `no`, `on`, `off`, `1` or `0` in any case: Claude Code accepts them since 2.1.218. Other values, such as `2` or `maybe`, still warn.
- `open-skill lint` reports a plugin or marketplace manifest nested too deeply to read (`manifest-json`) instead of crashing with `RecursionError`.
- `session update` sees changed files with non-ASCII names, such as `pkg/tóm tắt.py`: git quoted them (`"pkg/t\303\263m..."`), so they matched no session's scope and their conflicts went unreported. Git's output is also read as UTF-8 on Windows.
- On Windows, the output of `graphify update` (shown when a session refresh fails) and of the agent CLI behind `eval triggers` is read as UTF-8 instead of the locale code page, so non-ASCII paths and text are no longer garbled.

## [0.7.2] - 2026-09-29

Finishing the audit: concurrent writers, model fallback and repository checks.

### Fixed
- Two processes running `learn` at once no longer lose each other's scopes on a shared note: the read-modify-write holds a lock on `~/.open-skill/.lock` (POSIX; Windows has no lock yet).
- A model without its own profile falls back to the nearest profile of its family, the newest one not newer than the model (`claude-opus-5-1` → `claude-opus-5`; `claude-opus-4-7`, older than every profile, → `claude-opus-4-8`), instead of always the newest, whose effort names may be recalibrated; versions compare as numbers, not strings.
- The privacy guard and wheel check ignore an inherited `GIT_DIR`, `GIT_WORK_TREE` and `GIT_INDEX_FILE`, so they read the folder they are given; under `git rebase --exec` or a hook, the privacy guard's tests used to run `git add` against the repository itself.

## [0.7.1] - 2026-09-29

Follow-up fixes from the audit: sturdier user data, fairer keyword and trigger scoring, reviewed model profiles.

### Changed
- The Claude Opus 4.8 profile is verified against its full guide: effort xhigh for medium and large work and high for small (it inherited low/medium/high, below the guide's minimum), fewer subagents and a preference for reasoning over tool calls as traits, and notes on tool use, subagent fan-out and its fixed design house style.
- The `generic` model profile keeps only advice from the general prompting guide it cites; two notes taken from the Claude Fable 5 guide ("give a recommendation instead of a survey", "point to the tool result that shows it") move to the `claude-fable-5` profile, so other models and agents no longer receive them.
- Keyword routing no longer lets generic verbs decide a tie: "write a postmortem" targets learn, "write a data contract" specify and "write an ADR" plan. Symptoms (failing, broken, crash, hangs, debug) now beat build and release words, so "the deploy pipeline is failing" starts with debugging (operate). Topic words do not: alert, monitor, cost, and also error and `lỗi` ("add error handling", `lỗi chính tả`). "write tests" and "add a model with tests" stay build. Taxonomy phases may list `generic` and `symptoms` keywords, with `_i18n` blocks like `keywords`; `update` and `cập nhật` are new generic build verbs.
- The `eval triggers` lexical proxy scores descriptions with BM25 without length normalization, so the core skills' long SKILL.md descriptions no longer lose to short registry descriptions for the same matches, and adding an adapter moves fewer scores. Tuning recall rises to 0.90–1.00 and holdout recall from 0.00–0.17 to 0.67–0.83; holdout precision falls to 0.56–0.71 because the core skills now reach the top 3 at all. The floors in `tests/test_evals.py` follow.

### Fixed
- `route --model` finds the profile for provider-prefixed ids such as Amazon Bedrock's `us.anthropic.claude-opus-5-5-v1:0` or a gateway's `anthropic/claude-opus-5-5`; they fell back to `generic`, dropping the model's step limit and notes.
- `restore` unpacks beside the current state and swaps it in by renames, putting the old state back if anything fails (a full disk, a locked file); it used to delete the current files first and could leave a half-restored home, and restoring on a machine without `~/.open-skill` staged in the system temp folder, which fails when that is another drive.
- `restore` (and `upgrade --rollback`) refuse, with exit 2 and nothing changed, when a folder in `~/.open-skill` is a link; they used to crash on it after deleting other files.
- Backups (including the one taken before a migration) include notes in a linked folder, such as `knowledge/` pointing to a synced drive; they used to leave those notes out.
- A backup interrupted by a full disk no longer leaves a partial archive in `backups/` that `upgrade --rollback` or `restore` would take for a whole one; archives are written under a temporary name and renamed when complete.
- A read-only (or otherwise unwritable) `~/.open-skill` makes writes exit 1 with the path and the reason instead of a traceback, and `route` still prints its chain, warning that the route was not recorded.
- When `~/.open-skill/knowledge` is a file, writes and `export` stop with exit 2 before changing anything; `learn` used to migrate and back up first, then crash, and `export` wrote an archive without notes.
- A note whose frontmatter is not valid YAML no longer makes the data migration and seed sync fail on every write; the migration leaves it byte for byte as it is and says so.
- A `profile.yaml` that is not valid YAML, or not a mapping, stops every command with exit 2 and the line at fault instead of a traceback; the file is left as it is.
- A half-written last line in `events.jsonl` (a crash or a full disk mid-append) no longer breaks every route: damaged lines are skipped, and the next event starts on a line of its own instead of being glued to the broken one.
- `validate` with a broken `profile.yaml` exits 2 like every other command, instead of counting it as a registry error.
- CI checks: the privacy guard scans every tracked text file (including names with spaces or accents) and an allowed noreply address no longer clears the rest of its line; `check_versions` checks every pin, the READMEs too; revert pull request titles pass the title check; the oldest release's notes stop before the compare links; the wheel check requires every tracked data file and module.
- taste-skill skills installed with `npx skills add`, which names each folder after its frontmatter `name` (`design-taste-frontend`, `minimalist-ui`, ...), are detected under their registry ids instead of being harvested as unknown skills. Adapter skills may set `installed_as` for such a folder name (SPEC §4.1, §4.2).

## [0.7.0] - 2026-09-29

English-first and audited: the whole repository is written for an international audience with Vietnamese as a locale, every lint, audit and registry rule was checked against its source and real public skills, the core skills, adapters and role packs were reviewed against the CLI and upstream, every command is tested end to end, and the README is illustrated with generated diagrams and real terminal captures.

![How routing works](https://raw.githubusercontent.com/VoKhoiNhon/open-skill-standard/v0.7.0/.github/assets/routing.svg)

### Added
- Role coverage in the tuned routing evals: every role has at least 5 cases across at least 3 target phases, and every role pack primary is placed by some case (`tests/test_role_coverage.py`); 31 new cases close the gaps.
- `open-skill validate` rejects a role pack entry whose skill does not act in that phase, since the router never places it there.
- README images in `.github/assets/`, light and dark: the architecture, the routing pipeline (numbers read from `route.py`), the lifecycle graph (generated from the taxonomy and adapters) and what an upgrade does to your notes, plus terminal captures of `route --explain` for a backend developer, a data engineer and an SRE, `doctor`, `audit` and `upgrade --dry-run`, run on a fixture machine with no local paths. Graph viewer screenshots in light and dark come from `render_assets.py --screenshots`, a manual step with a local Chromium. `scripts/render_assets.py` regenerates them and CI fails when they are stale; the privacy guard now reads SVG text and rejects local home paths.
- `evals/routing-holdout.yaml`: 52 held-out routing cases (paraphrased and messy requests across 23 roles, English and Vietnamese with and without accents) that routing is never tuned on. `eval routing` reports in-sample and holdout scores apart (baseline 23/52); only in-sample failures change the exit code, and CI keeps the holdout above a floor. Routing cases gain `first_phase` and `include_any` assertions.

### Changed
- Starter knowledge: the full-stack seed that repeated the backend one ("update the client and the tests in the same change") is retired and replaced by `end-to-end-test-across-layers`; notes you already have are kept.
- Search stopwords are taxonomy data (`stopwords`, with Vietnamese in `stopwords_i18n.vi`) instead of a list in the code, so a new language adds its own; the set is unchanged.
- The four core skills' descriptions are English only; Vietnamese requests reach them through the adapter's `vi` blocks, which now mirror each skill's English triggers. Trigger queries carry `locale`, and `eval triggers` prints a slice per language (Vietnamese floors in CI); for such queries the proxy also reads the skills' locale words.
- Locale keywords: phase `keywords`, `size_keywords` and adapter `triggers` hold English only; other languages sit in `<field>_i18n` blocks keyed by language tag (`keywords_i18n: {vi: [...]}`), which the router, search and generated schemas read. Existing Vietnamese words moved into `vi` blocks with routing unchanged. A new language needs only new blocks (SPEC §3.1); keywords in scripts written without spaces (Japanese, Chinese, Thai) match inside the text. `validate` checks the taxonomy against its own generated schema.
- `open-skill lint` rules were checked against their sources (agentskills.io spec and its `skills-ref` validator, Anthropic's skills docs and `quick_validate.py`, the Claude Code skills, plugins and marketplace references, the model prompting guides). Each rule now has one severity and one cited source. Name and description checks are split into `frontmatter-name`, `name-ascii` (warning), `name-reserved-word`, `frontmatter-description` and `description-angle-brackets`. `temperature`/`top_p`/`top_k` are `sampling-params`. Paths only named in inline code are the `missing-mention` warning, a non-kebab plugin name is `plugin-name-style`, the "looks official" marketplace warning is `marketplace-reserved`, and a non-semver plugin version is now a warning (Claude Code does not check it). Known frontmatter fields follow the Claude Code reference (`arguments`, `disallowed-tools`, `background`, `shell` added; top-level `version` removed).
- Routing score: a skill's fit is now the better of role prior × saturating text relevance and text alone (BM25 / 6), instead of the product only, so a skill outside the role pack that the request clearly names (BM25 12 or more) can beat a primary with no text match; typical matches rank as before (SPEC §6.5). `--explain` marks steps that won on text alone. In-sample routing evals stay at 100%; the holdout is unchanged.
- The router skill has the agent classify the phase (the ten taxonomy ids) and size from the conversation and pass `--phase`/`--size`; keyword detection is the fallback, and a `guessed` phase is checked against the request. Its manual path starts from the same phase.

### Fixed
- Forgetting a seed also drops its pending upstream update, which otherwise stayed "to review" forever and made `seeds accept` crash.
- `install --project` must name an existing folder; a mistyped path used to be created along with the skill folders.
- `search --limit` and `eval triggers --runs` must be positive: `--limit -1` silently dropped the last hit and `--runs 0` crashed.
- `graph --out` creates the folders it needs, like `export` does.
- `init --role name=weight` with a weight that is not a positive number exits 2 instead of crashing (or storing a negative weight).
- `learn` with empty text exits 2 instead of crashing.
- `adapter check --from <missing folder>` exits 2 instead of reporting every skill as dropped upstream, and `eval triggers --cases <missing folder>` exits 2 instead of passing with an empty report.
- A missing or corrupt file given on the command line (`restore`, `eval --cases` and others) exits 2 with one line on stderr instead of a traceback.
- `forget` accepts only note ids: an id such as `../../notes` used to delete `notes.md` outside `~/.open-skill/knowledge/`.
- `upgrade` with nothing to do no longer makes a pre-upgrade backup and says "already up to date"; before, running it twice made `upgrade --rollback` restore the already-upgraded state.
- `validate` reports malformed registry documents (a seed or skill without its id or name, `null` lists, a YAML syntax error, a top level that is a list) with the file and field instead of crashing, and catches what used to pass silently: a skill listed twice in one adapter, two files of one layer with the same id, model inheritance cycles, a detect rule naming an unknown agent, and a hand-off to a role without a pack. The duplicate seed error names the ids.
- `audit`: false positives found by auditing five public skill repositories are gone (40 → 6 high findings), with every remaining one a literal match: "local state" and "web data" in prose are no longer browser data, quoted attack phrases in injection-defense guidance and `<system-reminder>` in backticks are not attacks, "never skip confirmation", "don't silently delete" and curly-apostrophe negations read as negations, `cp .env.example .env` and `cat > .env` are not secret reads, `<!-- prettier-ignore -->` is not a hidden instruction, hidden-comment only applies to Markdown and HTML, and shell-at-load only to SKILL.md and command files. UTF-16 files (PowerShell's default) are audited instead of skipped as binary, grants in folded `allowed-tools:` scalars are read, line numbers no longer drift after U+2028 or form feeds, and public `.pub` keys are not secret files.
- `upgrade --dry-run` and `seeds --dry-run` say "would keep your edit … upstream wording would wait for review" and "would keep … no longer shipped upstream" instead of claiming they saved or kept something.
- Seed sync no longer mistakes an untouched starter note for your edit when an editor re-saved it in decomposed Unicode (NFD, common on macOS); such notes follow new upstream wording again. Hashes of ordinary (NFC) text are unchanged.
- `route --explain` prints the role mix, project artifacts and a close call as plain text (`role=data-engineer 0.7, data-analyst 0.3`, `artifacts=spec, test-suite`, `ask the user: a or b`) instead of Python lists and dicts.
- A request to remember something ("remember that backfills run in bounded batches from now on") routes to `open-skill-learn` whatever its size; the skill was marked small-only, so a request sized medium got an empty chain.
- Role packs list skills only in phases they act in, so none of their entries is dead: BMad's self-critique (`bmad-advanced-elicitation`) moves from plan to review for the AI, platform and security engineers, the persona roundtable (`bmad-party-mode`) from verify to review for data scientists, the data scientist's build drops `explore-data` (already a research primary), the QA engineer's build drops two verify-only skills (the BMad test generator moves to its verify alternatives), and the product manager's verify drops the build-only `analyze`.
- The first route on a new machine no longer prints "upgraded your data" and runs a migration: reading notes created an empty `knowledge/` folder that made a fresh `~/.open-skill` look like an old layout. Dry runs no longer create folders either.
- Four adapter descriptions now say what the upstream skill does: `brand-guidelines` applies Anthropic's own brand (not any brand), `academy-guide` points to Claude Academy courses, `discernment-nudge` asks the user to check an answer before acting on it, and Context7's `context7-docs` is its Pi package.
- BMad's skills CLI install is copied verbatim from its README (`npx skills add bmad-code-org/BMAD-METHOD`, run in the project); the adapter had added `-g`.
- superpowers: the install commands its README gives for Cursor, Gemini CLI and GitHub Copilot CLI are offered to those agents (they were told to see upstream), and skills from the Gemini CLI extension (`~/.gemini/extensions/superpowers`) are detected. An agent's own `<key>@<agent>` command wins over the generic ones.
- Missing-skill hints fit the agent: spec-kit's `specify init` names the agent's integration key (`--integration codex`, `cursor-agent`, `gemini`, `copilot`…) instead of always `claude`, and points to upstream for an agent spec-kit does not support; Claude Code built-ins are no longer listed as missing for other agents with the hint "install claude-code-builtin". `install` keys may end in `@<agent>` (SPEC §4.1).
- Meta skills are never chain steps: BMad's `bmod-*` metadata records ("never invoke this skill"), superpowers' `using-superpowers` and addy's `using-agent-skills` session bootstraps, and `open-skill-router` itself were placed for discover tasks such as "what should the core tools module do". Adapter skills may set `kind: meta` (SPEC §4.1); `--why-not` names it.
- codegraph tools are routed when the `codegraph` CLI is on `PATH` and the project has `.codegraph/`; before, nothing could mark them installed, so they only ever appeared under `missing`. Adapters may set `available_cmd` (SPEC §4.1).
- Anthropic's skills installed as Claude Code plugins get the plugin name they are invoked by: every plugin of `anthropics/skills` copies the whole repository, so `document-skills` claimed `frontend-design` as `document-skills:frontend-design`. Detect rules may list `names` (SPEC §4.2), and the `claude-api`, `academy-guide` and `discernment-nudge` plugins are detected too.
- Role playbooks state the role's `build_window` ("Build tasks for this role walk discover → research → specify → plan"), so the router skill's manual path follows the same phases as the CLI for the 11 roles that have one.
- `learn` refusing text that looks like a secret or personal data names the `--force` flag instead of the Python argument `force=True`.
- A note scoped to a skill by the name the agent invokes it by (`skill:superpowers:writing-plans`, as the chain shows it) is attached to routes, not only one scoped by skill id.
- `learn --applies-to` rejects scopes no route can match (an unknown kind, role id or phase id) instead of saving a note that never applies, and resolves `project:` paths the way `route` does, so `project:.` or a symlinked path matches.
- `route --role` with an unknown role id (such as `frontend` for `frontend-developer`) exits 2 and lists the role ids, like `search` and `init` already did, instead of routing without any role pack.
- `feedback` for a route id that was never recorded (mistyped, or routed with `--no-record`) exits 1 and says so, instead of printing `recorded` for feedback that routing ignores.
- `feedback --ran` credits a skill run instead of the proposed one to that skill, so a correction such as "use superpowers here, not spec-kit" raises it in later routes; it used to be stored under a key routing never read. A proposed step named by its id also counts as run.
- `lint`: broken frontmatter is reported as `frontmatter` with the YAML line at fault, instead of "name is missing"; a BOM or an empty frontmatter block no longer loses the fields. Non-string names and descriptions (`name: 2024`, `description: ~`) no longer pass, and YAML alias trees are never expanded by `str()` (also in `scan` and `install`). Links inside code and placeholders like `[Title](URL)` are not reported missing. A 500-line file is not "over 500 lines", CJK text is no longer undercounted as tokens, and shouting in code blocks is ignored. Malformed `plugins` in marketplace.json no longer crash lint. `lint` on a missing path exits 2.
- Phase and size keywords match Vietnamese typed without accents (`xuat hoa don bi loi` is operate, `doi ten` is small) by folding like the search index; text typed with accents keeps them, so `lời` is not `lỗi`. Search also matches `đ` typed as `d`. Operate gains symptom keywords (slower, regressed, timeouts, "stopped working", "returns nothing", "since yesterday", and Vietnamese `không chạy`, `ngừng hoạt động`, `từ hôm qua` and more). Routing holdout: 23/52 → 36/52.
- `export` on a fresh `~/.open-skill` no longer creates an empty `knowledge/` folder either, so it too cannot make the home look like an old layout.
- `build --check` compares the search index `dist/index.db` row by row too; the shipped index had gone stale (it still folded `đ` the old way) without CI noticing, and is rebuilt.

## [0.6.0] - 2026-09-29

Multi-agent support, a security audit and graph explanations: install and scan skills for nine agents, audit skill folders before trusting them, and see why the router picks a skill.

### Added

**Multi-agent support**

- Agent targets in `registry/agents/`: Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot (CLI, coding agent, VS Code), OpenCode, Goose, Windsurf and Amp, with their global and project skill folders, how to detect each one and the documentation URL behind every path (SPEC §4.6).
- `open-skill scan` looks in the skill folders of every agent target and lists each skill once with the agents that see it; `scan --agent <id>` shows one agent's view under the names it invokes skills by. Detect rules may use `{skills}` and `{project_skills}` for every agent's folders, and may name an `agent` (SPEC §4.2).
- `open-skill agents [--project DIR] [--json]` lists the known agents, which are installed on this machine, how many skills each sees and where an install for it goes; `doctor` shows the detected agents.
- `open-skill install <core-skill-or-folder> --agent <id> [--project DIR] [--copy|--symlink] [--dry-run]` installs one of the four core skills or any local skill folder into that agent's skill folder. It never overwrites a different existing skill, leaves an identical one alone, and records every folder it creates, with file hashes, in `~/.open-skill/installed.json`. `doctor` suggests it for detected agents that do not see the router.
- `open-skill remove <skill> --agent <id> [--project DIR] [--dry-run]` removes only what `install` recorded: files still exactly as installed (never through a link), then folders left empty; files you changed or added stay. `open-skill update [--agent <id>] [--dry-run]` reinstalls installed core skills at the CLI's version and skips any install you changed.
- `route --agent <id>` and `search --agent <id>` use only the skills that agent sees, under the names it invokes them by (plugin names such as `superpowers:test-driven-development` are Claude Code only). Missing-skill hints fit the agent: `open-skill install … --agent <id>` for core skills, and outside Claude Code a non-plugin install command when the adapter has one, otherwise the upstream link instead of a Claude-only command. The router skill passes `--agent`.
- SPEC §5.2: guarantees for installing skills into agents (never overwrite, record with hashes, remove only unchanged recorded files, skip changed installs on update). README and README.vi describe the supported agents and the install, remove and update commands; a test keeps their agent tables in line with `registry/agents`.

**Security audit**

- `open-skill audit [paths] [--installed] [--format json] [--strict]`: a heuristic security review of skill folders (SKILL.md, references, scripts, assets) that only reads files. It flags instructions that override the user or system, hide actions, skip approvals, impersonate authority or reach for secrets, browser data and password stores; invisible characters and hidden HTML comments; broad `allowed-tools` grants and load-time shell commands; links leaving the skill and bundled executables. Every finding cites its source. Findings are grouped by source, exit 1 on high severity (any finding with `--strict`); `doctor` shows a one-line summary. A clean report does not mean a skill is safe.

**Graph viewer and explanations**

- `open-skill route --phase <id>` takes the target phase from the caller (an agent that read the conversation) and skips keyword detection; unknown ids exit 2. The JSON output gains `phase_from` (`given`, `keywords` or `guessed`), and `--explain` shows a phase picked without any signal as `phase: build (guessed, no signal)`. Build stays the fallback. Routing eval cases may set `phase`.
- `open-skill graph --format html --out graph.html` writes one self-contained page (no network) with skills by phase, artifacts and roles, filters by role, phase, source and installed state, search, keyboard use and a dark theme; `--out` works for every format. Graph JSON nodes now carry skill descriptions and role names.
- `open-skill route "<task>" --why-not <skill>` explains why a skill is not in the chain: not installed, wrong phase or size, requirement unmet, conflict with a chosen skill, below the minimum score, lower score than the winner (both scores), dropped by the model step limit, or done directly. `route.route(..., decisions=True)` exposes every candidate decision; the default output is unchanged.
- `open-skill search` filters: `--role`, `--phase`, `--source` and `--installed`, applied before `--limit`; without a query it lists every skill the filters keep.
- `open-skill route --explain` shows the target phase and size with the keywords that decided them, the phase window with why it was chosen (size, spec/plan/tasks in the project, the role's `build_window`), and up to three runner-ups per step with their scores.

**Routing and trigger quality**

- Trigger sets grow to 32 queries per core skill, with multilingual phrasing and closer near misses; the 12 new ones per skill are marked `holdout: true` and kept out of tuning.
- `eval triggers` reports the lexical proxy on tuning and holdout queries separately and lists failures for tuning queries only; `--agent` uses the `holdout` flags as its validation split when a set has them.
- Routing evals for the engineering and quality-ops roles: bug, crash and incident reports, reviews, research, postmortems, Vietnamese phrasing, and spec-kit and BMad projects.
- Routing evals for the data and AI roles: broken pipelines, models and reports, DAG and dbt reviews, reconciliation, dashboards, research, Vietnamese phrasing, and spec-kit and BMad projects.
- Routing evals for the architecture, leadership and product roles: reviews, research, retrospectives, roadmaps, PRDs and user stories, Vietnamese phrasing, and spec-kit and BMad projects. Every role now has at least three cases.
- `eval triggers --suggest`: words and phrases common to missed tuning queries and absent from the description, and description words that cause false alarms.
- Adapter for [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (25 engineering lifecycle skills, MIT), watched by the adapter-drift workflow. SREs build alerts and tracing with `observability-and-instrumentation`, security engineers build fixes with `security-and-hardening`, and DBAs plan zero-downtime migrations with `deprecation-and-migration`.
- Adapter for [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) (9 skills, MIT), watched by the adapter-drift workflow; its detect rules follow the skills CLI, which installs four of them under a `vercel-` prefix. React Native builds use `react-native-skills`, and frontend deploys to Vercel use `deploy-to-vercel`.

**Release tooling**

- `scripts/release_check.py X.Y.Z`: before tagging, verifies the version is bumped everywhere, nothing is left under `[Unreleased]`, the new section is the newest, dated and moves the version forward, and the compare links are updated. CI runs it on `release/*` pull requests.

### Changed
- Core skill bodies tightened: open-skill-standards reports failures and unverified items and reuses existing test output; open-skill-intel stops at the first source that answers; open-skill-router passes `--model` only when the id is known and its manual path no longer points at itself; open-skill-learn states its reason without claims about models.
- The open-skill-router, open-skill-standards and open-skill-learn descriptions say when to use them more plainly (the order of skills and work with several steps; checks before calling work done, ADRs and commit messages; notes scoped to a role, project or skill). Lexical proxy recall on tuning queries 0.60 → 0.70, 0.70 → 0.80 and 0.70 → 0.90; holdout scores unchanged except one learn false alarm fewer.
- The release workflow stops before building when the CHANGELOG has no section for the tag, with one clear error.
- Releases are titled `vX.Y.Z — <theme>` automatically, from the first line of the CHANGELOG section (`scripts/changelog.py title`).
- README and README.vi: a "See and question the graph" section with example output for `route --explain`, `route --why-not`, search filters and the HTML graph; the CLI reference lists the new flags.

### Fixed
- Crash and hang reports, in English and Vietnamese ("crashes", "hangs", `bị treo`, `văng`), start with debugging instead of a planned build.
- Embedded builds in spec-kit projects use `spec-kit/implement` instead of subagent-driven development.
- In spec-kit projects, cloud, security and SRE work plans with `spec-kit/plan`, and sysadmin work builds with `spec-kit/implement`.
- The Vietnamese `sự cố` (incident) leads to incident response rather than debugging.
- Analytics engineers build with the project's native framework (`spec-kit/implement`, `bmad-build`); AI engineers build with `bmad-build` in BMad projects; platform engineers plan with `spec-kit/plan` in spec-kit projects.
- Problem reports for data analysts, ML engineers and platform engineers start with debugging instead of proposing a scheduled agent.
- `bmad-ticket`, `bmad-architecture` and `bmad-prd` handle medium tasks, so BMad projects plan sprints, architecture and PRDs with BMad instead of an unrelated BMad persona or a generic skill.
- Technical writers review docs with code review instead of design critique outside BMad projects.
- A later detect rule of the same adapter no longer claims a path an earlier rule already found, so a prefix rule such as `{skills}/vendor-{name}` does not add a duplicate inferred skill.

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

[Unreleased]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.7.2...HEAD
[0.7.2]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/VoKhoiNhon/open-skill-standard/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/VoKhoiNhon/open-skill-standard/releases/tag/v0.1.0
