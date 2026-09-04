# Changelog

All notable changes to this project will be documented in this file.

## [2.4.0] - 2026-09-04

### Added

- **`glossary.json` — a structured vocabulary artifact for machine consumers**
  ([#10](https://github.com/TheGlitchKing/babel-fish/issues/10)). Written to
  `.claude/project-map/glossary.json` on every map build and staged by the
  pre-commit hook. Consumers read this instead of parsing `01-vocabulary.md`.

  The markdown was never a good parsing target: its `Notes` column mixes
  descriptions with metadata, and pipe-escaping leaks into values — this repo's
  own output contained `(auto \| nudge \| off)`. The JSON carries the real
  string.

### Fixed

- **The glossary contract described a format babel-fish has never emitted.**
  `glossary-contract.md` v1.0 specified bullet entries
  (`- **key** → \`path\` — desc`) and stated that non-conforming bullets are
  ignored; the generator has always written a markdown table. A consumer built
  strictly to that spec would extract **zero entries**. Rewritten (v2.0) around
  `glossary.json`, with the markdown documented as human-facing output that is
  not parsed.

- **Both sides of that contract documented a directory neither produces.** The
  contract, the integration guide and the README referred to `.babel-fish/`;
  babel-fish writes `.claude/project-map/`. The same error is mirrored in
  semantic-memory's `smart-middle-activation.md` and `corpora-json.md`, where it
  would have made Phase 3.1.0 find nothing — silently. Corrected here and filed
  there as
  [semantic-memory#28](https://github.com/the-glitch-kingdom/semantic-memory/issues/28).

- **`--project-root` crashed the generator.** `write_glossary()` computed the
  source path with `SECTIONS_DIR.relative_to(PROJECT_ROOT)`, but `SECTIONS_DIR`
  is bound to the script's own location, so pointing `--project-root` elsewhere
  raised `ValueError`. Found by a test written for the new artifact.

- `integration-with-semantic-memory.md` no longer describes a setup that does
  not exist. semantic-memory 1.5.1 ships no `translate` verbs, no `project-map`
  corpus and no glossary reader; the guide now says so at the top instead of
  giving instructions for it.

### Note

The consumer is unbuilt, so nothing was pinned to the old format. Issue #10
originally advised caution about "a breaking change to a format a downstream
consumer pins to" — checking semantic-memory's source showed zero
`translate`/`reverse_translate`/`list_vocabulary` verbs in its 164-entry tool
surface and no `glossary` string in `src/`. That freed the format choice
entirely.

## [2.3.0] - 2026-09-04

### Fixed

- **The grader could not tell a useless map from a good one**
  ([#9](https://github.com/TheGlitchKing/babel-fish/issues/9)). All seven graded
  categories measure *form*, and `generate.py` always emits well-formed output,
  so the completely empty pre-2.1.0 map scored **97.0% PASS** — identical
  category-for-category to the populated map. Verified against the real artifact
  recovered from git, not a reconstruction.

  Rather than reweighting, usefulness is now reported as **warnings that never
  touch the score**, so no existing install flips from pass to fail:

  - `generate.py` records *inputs* beside outputs (`### Source files scanned`).
    "0 routes" cannot be judged alone; "0 routes from 47 Python files" can. The
    counts already existed in `main()` and were being discarded.
  - An empty vocabulary warns — that is what babel-fish is for, so zero entries
    means the map gave you nothing. This fires on the real pre-2.1.0 map and is
    the signal that would have surfaced #6 at install time.
  - Ten or more source files scanned with nothing extracted warns separately,
    catching a parser that does not fit the stack. Small repos stay quiet.
  - A populated-sections count prints as an explicit diagnostic.

- **The greenfield branch in `grade_vocabulary_accuracy()` was unreachable.**
  `build_vocabulary_section()` emitted a placeholder *table row* for an empty
  vocabulary, which parsed as a valid entry whose blank location counts as
  neutral — scoring 1/1 = 100% and stepping straight over the `if not rows`
  branch written to award 85%. It now emits prose.

- **`or '_No' in content` matched too much.** Any italicised word beginning
  "No" (`_Note`, `_Nothing`) anywhere in `12-import-chains.md` scored a
  populated section as an acceptable empty one at a flat 80%.

### Fixed (packaging)

- **The npm tarball shipped local and generated files.** `files` listed
  `.claude/` wholesale, and npm does **not** honour `.gitignore` for paths named
  there — so every release carried this repo's own generated project map,
  another plugin's local state (`.claude/.semantic-memory/`), five plugins'
  update caches, ~150 kB of `__pycache__` bytecode, and
  `.claude/settings.local.json`. `files` now lists only what
  `.claude/install.sh` actually copies plus the test suites. Also anchored
  `checksums.json` to `./checksums.json`: a bare filename in `files` globs at
  any depth, so it was matching `.claude/project-map/checksums.json` too.

  Tarball: 76 files / 140.9 kB → **33 files / 65.6 kB**. Verified by installing
  from the packed tarball into a scratch project.

### Added

- 9 tests in `test_grader.py`, 7 of which fail against the previous code.
  `npm test` now runs three suites (8 + 12 + 9 = 29).
- `architecture/grading-semantics.md` — what the score means, what it
  deliberately omits, and the measurements behind that choice.

### Not done, deliberately

Issue #9 originally proposed scoring section completeness on populated content.
Measured and withdrawn: it fails the *correct* map too (85.2%), because 19
sections is aspirational — a plugin repo can never populate routes, models,
schemas or migrations, so `populated/19` tops out near 10/19 on a perfect map.
It would fail every legitimately sparse repo, a worse failure than the one it
fixes. The 90% threshold and the category weights are unchanged.

## [2.2.0] - 2026-09-04

### Fixed

- **Session vocabulary mining has never worked**
  ([#7](https://github.com/TheGlitchKing/babel-fish/issues/7)). The issue
  reported that `mine-sessions.py` has no caller. It also had six defects, each
  sufficient on its own to make it extract nothing — it exited 0 reporting
  "Extracted 0 alias(es)" for its entire existence, which is why they survived.

  1. **Wrong JSONL nesting.** Read `msg['content']`; Claude Code writes
     `msg['message']['content']`. Measured on a real transcript: 0 vs 157
     `tool_use` blocks, 0 vs 14 user messages. Both halves of the pairing were
     empty.
  2. **Invalid regex quantifiers.** `{2,40?}` and `{2,30?}` are malformed brace
     expressions that Python silently treats as literals, so both patterns
     compiled and matched nothing — including the one implementing this
     feature's own README example, "the numbers page".
  3. **Tool results collide with user turns.** Results arrive as `role: "user"`
     (167 of 181 in one transcript), so the pairing window closed on the
     assistant's own output.
  4. **Bash file access was invisible.** A real session ran 148 Bash calls
     against 2 Read and 2 Edit; only 4 of 157 tool calls qualified.
  5. **Injected text was mined as user speech.** Skill and slash-command bodies
     arrive in the user slot, and taught the miner aliases from the injected
     documents themselves (`block_index_edits`, `refactor authentication
     system` — the latter from a skill's worked example). Now skipped via
     `isMeta` / `isSidechain`.
  6. **Session discovery never matched exactly.** `.lstrip('-')` stripped the
     leading separator that `~/.claude/projects/` slugs keep, so every lookup
     fell through to a fuzzy substring match that also ran additively — and a
     name like `kentro` matches four unrelated projects, whose aliases would be
     attributed to this repo.

  Verified against 220 MB of transcripts for a real product repo: 0 aliases
  before, 170 after, reading like genuine domain vocabulary (`sign-up` →
  `payments.py`, `pricing` → `subscription_gate.py`).

- **`README.md` claimed mining happened "automatically".** It did not — nothing
  called the miner. Now true, and documented with its two real caveats.

### Added

- **Mining runs at session start.** `hooks/session-start.js` spawns the miner
  detached with output discarded and nothing awaited; it cannot delay or fail a
  session, and no-ops when Python or the script is absent.
- **Incremental cursor** (`.mine-cursor.json`). Not only a cost guard:
  `merge_learned()` adds scores, so re-mining a counted transcript inflates it
  without bound. `--all` forces a full re-mine.
- 12 tests in `test_mine_sessions.py`, one per defect plus an end-to-end mine.
  All 12 fail against the previous miner. `npm test` runs both suites (20).
- Docs: `architecture/session-vocabulary-mining.md` (including the transcript
  shape assumptions the miner depends on but does not control) and
  `troubleshooting/learned-vocabulary-empty.md`.

### Known issues

- Aliases land one session late: SessionStart mines transcripts through the
  previous session, since the current one isn't written yet.
- Phrase quality is heuristic. Filtering drops clause-like candidates, but a
  quoted string in a user message can still become an alias.

## [2.1.1] - 2026-09-04

### Fixed

- **Section 19 listed generated hit-em-with-the-docs reports.**
  `.documentation/reports/` holds timestamped audit output, so every `hewtd
  maintain` wrote a new filename, which changed the doc path set, moved the
  checksum and forced a full map regeneration — the exact churn the path-only
  doc hash exists to prevent, reintroduced through a directory that was
  gitignored but never excluded from the doc walk. `reports` joins `archive` in
  `DOC_SKIP_DIRS`. Regression test added; it fails without the fix.

## [2.1.0] - 2026-09-04

### Fixed

- **Plugin and skill repositories no longer generate an empty project map**
  ([#6](https://github.com/TheGlitchKing/babel-fish/issues/6)). Run babel-fish
  against a repo of markdown skills, slash commands and bash scripts and every
  one of the 19 sections came back a "none detected" stub. Two causes, both
  fixed:

  - The checksum was blind to the files that define such a repo.
    `collect_watched_files()` returned 11 files for babel-fish's own repository,
    with no `.md` and no `.sh`, so editing a `SKILL.md` left the checksum
    bit-identical and `is_unchanged()` exited before parsing. Skill and command
    manifests are now matched by path glob (`skills/*/SKILL.md`,
    `commands/*.md`), and `.sh` joins `WATCHED_EXTENSIONS`.
  - Nothing read those manifests. `SkillParser` now feeds skill and command
    frontmatter into section 01 (vocabulary) and section 10 (tools) — the two
    sections they already fit. No new sections, no renumbering.

  Measured on this repository: 0 vocabulary entries to 10, sections 2,589 bytes
  to 4,389. On `hit-em-with-the-docs`, an unrelated plugin repo: 0 to 30.

- **Section 19 missed `.documentation/` trees and went stale silently.** Doc
  directories were never watched, so adding a document did not move the
  checksum and the pointer list rotted until an unrelated source file happened
  to change. Doc paths are now hashed **without** mtime: adding, renaming or
  deleting a document refreshes section 19, while editing one does not force a
  full regeneration. `.documentation` joins the doc directories, and generated
  navigation (`INDEX.md`, `REGISTRY.md`) plus `archive/` are excluded — without
  that, a 15-domain tree contributes 32 nav files and crowds every real
  document out of the 30-entry cap.

- **`checksums.json` was stale**, so the documented curl installer aborted with
  `CHECKSUM MISMATCH` for everyone. `.claude/install.sh` was edited in `da8d2f7`
  without regenerating the manifest.

### Added

- First tests in the repository: `npm test` runs an 8-test regression suite over
  a fixture repo shaped like #6. Stdlib `assert`, no framework. Verified to fail
  7/8 against the pre-fix generator rather than merely passing after it.
- `.documentation/` docs for the watch set, the skill parser contract, and an
  empty/stale map troubleshooting guide; operational runbook gained the
  corresponding gotchas.

### Known issues

- `grader.py` scores a completely empty map at 97.0% PASS, the same as a fully
  populated one — "Vocabulary Accuracy" is 100% on zero entries because
  0/0 = 100. It measures well-formedness, not usefulness, and must not be used
  to confirm an extractor fix. Left unchanged here: adding a floor would fail
  existing installs that currently pass.
- `01-vocabulary.md` is emitted as a markdown table, while
  `.documentation/api/glossary-contract.md` specifies `- **key** → \`path\``
  bullets. A consumer implemented strictly to that contract extracts zero
  entries. Predates this release; which side moves is undecided.

## [2.0.3] - 2026-06-08

### Fixed

- Release-metadata consistency: the 2.0.2 npm payload shipped with
  `.claude-plugin/plugin.json` still at version 2.0.0 (the manifest bump landed
  after the 2.0.2 publish), so Claude Code read the installed plugin as 2.0.0
  and `claude plugin update` never advanced. 2.0.3 bumps `package.json`,
  `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json` together
  before publishing so the plugin version resolves correctly. No code change
  from 2.0.2.

## [2.0.2] - 2026-06-08

### Fixed

- Internal lint cleanup in `generate.py`: removed an unused `os` import and
  two unused local variables, and dropped the `f` prefix from five
  placeholder-less f-strings (ruff F401/F841/F541). No behavior change.

## [2.0.1] - 2026-06-08

### Fixed

- **Frontend feature scanner now detects monorepo layouts.** `FrontendScanner`
  previously looked for `features/`, `pages/`, `views/`, etc. only at the repo
  root or under a top-level `src/`. Projects that keep the frontend in a
  subpackage (e.g. `frontend/src/features/`, the common React/Vite plus Python
  backend split) were reported as "No frontend feature directories detected,"
  leaving project-map sections 09 (Frontend Features) and 13 (Frontend to
  Backend Map) empty. The scanner now searches `frontend/`, `web/`, `client/`,
  and `ui/` (each with an optional `src/`) in addition to the repo root and
  `src/`, dedupes by resolved path, and only emits directories that actually
  contain `.jsx`/`.tsx` files so a backend package named `app/` is not
  misclassified as a frontend feature.

## [2.0.0] — 2026-04-19

### Breaking changes

- **Package is now ESM (`"type": "module"`).** If anything imports from
  `@theglitchking/babel-fish` via `require()` (the package has no `main`,
  so this is unlikely), you'll need to switch to `import`. The CLI
  (`npx @theglitchking/babel-fish <cmd>`) is unaffected.
- **Node >= 20** (was >= 16). Matches the rest of the Glitch Kingdom
  plugin ecosystem and the runtime.
- CLI is now `commander`-based. Subcommands, flags, and arguments
  behave the same as before — `init`, `dry-run`, `regen`, `grade`, and
  `help` all work identically — but you now also get `--help` and
  `--version` on every subcommand.

### Migration

No user-facing code changes required — just:

```bash
npm install @theglitchking/babel-fish@latest

# Or if you used the curl|bash installer (unaffected):
curl -sSL https://raw.githubusercontent.com/TheGlitchKing/babel-fish/main/install.sh | bash
```

Your existing `.claude/project-map/` infrastructure and `.githooks/pre-commit`
keep working — this release doesn't touch them. The only net-new files
added to your project are `.claude/babel-fish.json` (update policy —
defaults to `nudge`) and a SessionStart hook entry in
`.claude/settings.json` (only if that file exists and the plugin
marketplace version isn't already handling it).

### Added

- Adopts
  [`@theglitchking/claude-plugin-runtime`](https://github.com/TheGlitchKing/claude-plugin-runtime)
  (`^0.1.0`) for standardized update management and postinstall wiring.
- **Postinstall** (`scripts/link-skills.js`) symlinks
  `skills/babel-fish-developer-skill/` into `<project>/.claude/skills/`
  so Claude Code picks it up automatically. If you later run
  `npx @theglitchking/babel-fish init`, the install script's `cp`
  replaces the symlink with a regular copy — either way the skill is
  discoverable.
- **SessionStart hook** (`hooks/session-start.js`) checks npm for a
  newer version at session start and acts per policy (off / nudge /
  auto). Default is `nudge` — a one-liner notification, no automatic
  changes.
- **Slash + CLI subcommands:**
  - `/babel-fish:update` / `babel-fish update`
  - `/babel-fish:policy [auto|nudge|off]` / `babel-fish policy`
  - `/babel-fish:status` / `babel-fish status`
  - `/babel-fish:relink` / `babel-fish relink`

### Opt-outs

| Variable | Effect |
|---|---|
| `BABEL_FISH_UPDATE_POLICY` | One-shot policy override |
| `BABEL_FISH_SKIP_LINK=1` | Skip skill symlinking in postinstall |
| `BABEL_FISH_SKIP_HOOK_REGISTER=1` | Skip writing the SessionStart hook into `.claude/settings.json` |

---

## [1.0.2] and earlier

See git history:
https://github.com/TheGlitchKing/babel-fish/commits/main
