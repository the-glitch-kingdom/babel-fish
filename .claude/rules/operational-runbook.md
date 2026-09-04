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
| `npm test` | Run the project-map regression suite (8 tests) |
| `python .claude/project-map/generate.py --force` | Force-regenerate project map |
| `python .claude/project-map/grader.py` | Grade map quality (0-100%) |
| `bash .githooks/install.sh` | (Re)install git hooks |
| `bash .claude/install.sh` | Re-run full plugin installer |

## Dev Credentials

<!-- Add test/dev credentials here (NEVER production secrets) -->
