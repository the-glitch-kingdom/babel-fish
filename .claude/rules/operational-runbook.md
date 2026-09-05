# babel-fish — Operational Runbook

> Auto-loaded every session. Contains operational knowledge that cannot be derived from code.
> This file grows over time as the team discovers gotchas, quirks, and procedures.
> **Edit this file manually** — it is NOT overwritten on regeneration.

## Environment Differences

<!-- TODO: Document how dev/staging/prod differ (DB, deploy method, secrets, URLs) -->

| | Dev | Staging | Production |
|---|---|---|---|
| **URL** | | | |
| **Database** | | | |
| **Deploy** | | | |
| **Secrets** | | | |

## Known Issues & Workarounds

<!-- This section fills in naturally. When you hit a non-obvious issue, add it here. -->
<!-- Examples: "HMR doesn't work on WSL2", "port 6543 breaks migrations" -->

### A passing grade does not mean a useful map

`grader.py` scores a completely empty map at **97.0% PASS** — identical to the
score it gives a fully populated one. "Vocabulary Accuracy" reads 100% on zero
entries (0/0 = 100) and "Section Completeness" counts a stub as complete. It
measures well-formedness, not usefulness.

Never use the grade to confirm a parser or extractor fix. Run `npm test`.

Since 2.3.0 the grader prints usefulness warnings below the score — "Vocabulary
is empty" and "Scanned N source files but extracted nothing". Those are the
lines worth reading; they do not affect pass/fail.

### "No changes detected" after editing a file

Only files in the watch set move the checksum. If `generate.py` skips
regeneration after a real edit, the file is not watched — check
`WATCHED_EXTENSIONS`, `WATCHED_GLOBS`, and `IGNORE_DIRS`. `--force` always
bypasses it.

Anything under `.claude/` is parsed (via direct globs) but never watched, so
edits there refresh only on the next run triggered by something else.

Full symptom table: [`.documentation/troubleshooting/map-is-empty.md`](../../.documentation/troubleshooting/map-is-empty.md)

### Editing a doc body never regenerates the map

By design. Doc paths are hashed without mtime, so adding/renaming/deleting a doc
refreshes section 19 while editing one does not churn the whole map. Section 19
lists paths, never content.

### Learned vocabulary mines nothing — often correct

The miner learns feature nouns ("the deals page"). Sessions spent on tooling,
refactoring or releases contain few and correctly yield zero. It also never
raises: it exits 0 printing "Extracted 0 alias(es)" whether it worked or is
broken, so silence is not evidence either way.

Aliases land one session late — a transcript isn't written until its session
ends, so SessionStart mines through the previous session.

Full symptom table: [`.documentation/troubleshooting/learned-vocabulary-empty.md`](../../.documentation/troubleshooting/learned-vocabulary-empty.md)

### Never delete .mine-cursor.json alone

`merge_learned()` ADDS scores. The cursor is what stops an already-counted
transcript being re-counted. Deleting it without also resetting
`learned-vocabulary.json` double-counts every historical session.

### The curl installer aborts with CHECKSUM MISMATCH

`checksums.json` holds the SHA256 of `.claude/install.sh` and is verified before
execution. Any edit to that installer requires regenerating the manifest:

```bash
sha256sum .claude/install.sh    # write the result into checksums.json
```

This has gone stale more than once (commit `a2dad3f` was a prior fix for the
same thing). If the documented curl one-liner aborts, check this first.

### A green suite is not proof the tree is clean

Until #18, `npm test` rewrote `.claude/project-map/glossary.json` with fixture
data and still reported every test passing — the glossary silently dropped from
10 entries to 1 mid-release.

`generate.py` and `mine-sessions.py` bind their output paths (`MAP_DIR`,
`SECTIONS_DIR`, `CHECKSUMS`, `LEARNED_VOC`, `GLOSSARY`) at **import time** from
`__file__`, and rebind them only inside `configure_paths()`. Setting
`PROJECT_ROOT` alone — in a test loader or anywhere else — leaves every write
aimed at the real repo while the caller believes it is in a temp fixture.

When adding a test that calls a writer, load the module with
`configure_paths(fixture_root)`, never `mod.PROJECT_ROOT = fixture_root`, and
run `git status` after the suite. `test_grader.py` is the exception: its loader
assigns a *map dir*, not a project root.

### `update` and `status` behave differently per install kind

babel-fish installs two ways, and they are not interchangeable:

- **npm project dep** (`node_modules/`) — `update` can actually update it.
- **Claude Code plugin** (`~/.claude/plugins/cache/`) — only `/plugin` can.
  npm cannot touch that copy; `update` says so and exits 1.

Both are resolved by `resolveInstall()` in `@theglitchking/claude-plugin-runtime`
(≥0.1.1), which also reads `~/.claude/plugins/installed_plugins.json`. Before
0.1.1 it looked only at `node_modules` and `CLAUDE_PLUGIN_ROOT`, so a plugin
install reported `(not installed)`, ran a no-op `npm update`, and **exited 0**
(#17). If `update` or `status` ever reports `(not installed)` against a working
CLI, check the runtime version first.

Two consequences for tests and scripts: anything that shells out to `update` or
`status` must override `$HOME`, or its result depends on which plugins the
person running it happens to have installed. And a marketplace plugin registers
its SessionStart hook through its own `hooks/hooks.json` — an empty
`.claude/settings.json` is not evidence the hook is missing.

### Raising a shared dep needs a floor bump, not just a caret

All the sibling plugins resolve `@theglitchking/claude-plugin-runtime` from one
shared tree at `~/.claude/plugins/npm-cache/`, whose lockfile pins a single
version for every plugin at once. Publishing 0.1.1 does not reach them: 0.1.0
still satisfies `^0.1.0`, so the locked copy survives.

Raise the floor (`^0.1.1`) in the plugin's own `package.json` and republish the
plugin. That invalidates the lock entry and forces re-resolution. 2.4.2 and
persistent-planning 3.4.2 both exist for this reason alone.

Note this repo gitignores `package-lock.json` (`.gitignore:4`), so there is no
lock here to pin anything — the range in `package.json` is the only control.

### Releases must bump three manifests together

`package.json`, `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
all carry the version. 2.0.3 exists solely because the 2.0.2 npm payload shipped
with `plugin.json` still at 2.0.0, so Claude Code read the installed plugin as
2.0.0 and `claude plugin update` never advanced.

## Deploy Procedures

<!-- TODO: Document how to deploy to each environment -->

## Key Commands

| Command | What It Does |
|---------|-------------|
| `npm test` | Run all three project-map suites — generate (15), mine-sessions (13), grader (10). Stops at the first suite that fails, so a low count means an early exit, not a small suite |
| `python .claude/project-map/generate.py --force` | Force-regenerate project map |
| `python .claude/project-map/grader.py` | Grade map quality (0-100%) |
| `bash .githooks/install.sh` | (Re)install git hooks |
| `bash .claude/install.sh` | Re-run full plugin installer |

## Dev Credentials

<!-- Add test/dev credentials here (NEVER production secrets) -->
