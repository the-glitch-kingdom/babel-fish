# babel-fish — Operational Runbook

> Loaded every session, so it holds pointers, not detail. Edit by hand; never regenerated.

## Adding an entry

One **pointer record** per entry: what you see, the one-line fix, `→` the doc with the detail.
Write the detail the hewtd way first: a gotcha as a fact under `.documentation/knowledge-base/facts/`
(tagged `gotcha`, `## Instead`, `verify_command`), anything else as a doc in its domain folder,
then `hewtd maintain`. Never a secret or credential here, only the variable's name.

## Environments

None deployed: babel-fish ships as an npm package and a Claude Code plugin. Releases are below.

## Known Issues & Workarounds

### Project map

- **The grader passes an empty map (97% PASS)**: it measures form, not usefulness; confirm a parser fix with `npm test` and read the warnings under the score. → `.documentation/architecture/grading-semantics.md`
- **A grader Secret Safety hit**: some write path bypassed `redact_secrets()`; route it through, never loosen the pattern, rotate anything ever committed. → `.documentation/knowledge-base/facts/map-env-section-never-holds-values.md`
- **"No changes detected" after a real edit**: the file is outside the watch set (`.claude/` is never watched); `--force` bypasses it. → `.documentation/architecture/project-map-watch-set.md`
- **Editing a doc body doesn't regenerate the map**: by design, docs hash without mtime. → `.documentation/architecture/project-map-watch-set.md`
- **Learned vocabulary mines nothing**: often correct, lands one session late, and silence proves nothing; never delete `.mine-cursor.json` alone (double-counts). → `.documentation/troubleshooting/learned-vocabulary-empty.md`

### Tests and hooks

- **A green suite while the real repo changed**: writers bind output paths at import; load them with `configure_paths()`, check `git status` after. → `.documentation/knowledge-base/facts/writers-bind-output-paths-at-import.md`
- **The pre-commit hook never runs**: `git config core.hooksPath` must print `.githooks` and the hook must be executable. → `.documentation/standards/auto-loaded-context-check.md`
- **"[context-check] Commit blocked"**: over budget or a dangling pointer; the FAIL lines say which. → `.documentation/standards/auto-loaded-context-check.md`
- **"[structure-check] Commit blocked", or it never runs**: opt-in, passes silently on Python < 3.11, checks the repo it's installed in; never widen `holds`. → `.documentation/troubleshooting/structure-check-failures.md`
- **A hook change never reaches installed repos**: the installer never rewrites an existing hook block; change both copies. → `.documentation/knowledge-base/facts/installer-never-rewrites-an-existing-hook-block.md`

### Install and update

- **The curl installer aborts with CHECKSUM MISMATCH**: regenerate `checksums.json` with every `install.sh` edit. → `.documentation/knowledge-base/facts/installer-checksum-must-match-install-sh.md`
- **`update`/`status` says "(not installed)"**: npm and plugin installs differ; check the runtime is 0.1.1+. → `.documentation/knowledge-base/facts/update-and-status-differ-by-install-kind.md`
- **A runtime fix doesn't reach the plugins**: raise the floor in `package.json` and republish. → `.documentation/knowledge-base/facts/shared-dep-fix-needs-a-floor-bump.md`

## Releases

- **Bump all three manifests together**, then date the CHANGELOG, tag `vX.Y.Z`, push. → `.documentation/knowledge-base/facts/releases-bump-three-manifests.md`
- **`npm publish` fails with EOTP**: use a token with 2FA bypass, through a temporary userconfig. → `.documentation/knowledge-base/facts/npm-publish-token-needs-2fa-bypass.md`

## Key Commands

| Command | What It Does |
|---------|-------------|
| `npm test` | All five project-map suites; stops at the first failing suite, so a low count means an early exit |
| `python .claude/project-map/generate.py --force` | Force-regenerate the project map |
| `python .claude/project-map/grader.py` | Grade map quality (form, not usefulness) |
| `python .claude/project-map/context-check.py` | Budget + pointer check on auto-loaded files (what the hook runs) |
| `python .claude/project-map/structure-check.py` | Check files against `.claude/structure.toml` (`--detect`, `--bootstrap`) |
| `bash .githooks/install.sh` | (Re)install git hooks |
| `bash .claude/install.sh` | Re-run the full plugin installer |
