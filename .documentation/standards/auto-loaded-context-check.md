---
title: Auto-loaded context check
tier: standard
domains:
  - standards
audience:
  - all
tags:
  - python
status: active
last_updated: 2026-09-25
version: 1.0.0
purpose: Documentation for auto-loaded context check
estimated_read_time: 1 minute
word_count: 162
last_validated: 2026-09-25
backlinks: []
---

# Auto-loaded context check

`CLAUDE.md` and every `.claude/rules/*.md` load into **every** Claude Code
session. Past the harness limit (150k chars) the harness warns and rules stop
binding reliably — nothing else reports it. Before that, growth is one
paragraph at a time and nobody sees the total.

`.claude/project-map/context-check.py` keeps those files small and pointing at
things that exist. It came from [#20](https://github.com/TheGlitchKing/babel-fish/issues/20),
upstreamed from glitch-stock-trading-rig, whose auto-loaded files had reached
225.6k chars.

## What it checks

| Check | Default | Fails when |
|---|---|---|
| Budget | on, 60,000 chars | the total of every auto-loaded file exceeds `--budget` |
| Pointers resolve | on | a pointer names a path that does not exist |
| Rule lines | **off** — `--map-style` | a rules-file bullet is not `` - ALWAYS\|NEVER <rule> — <why> → `doc` `` |

**Files counted:** `CLAUDE.md`, `CLAUDE.local.md`, `.claude/CLAUDE.md`, and
`.claude/rules/**/*.md`. Rules with `paths:` frontmatter load lazily but are
counted anyway — over-counting errs toward the budget, not past the limit.

**Pointers recognised:**

- `` → `path.md` `` and backticked `` `.documentation/…md` `` — root-relative.
- Markdown links `[text](path)` — pass if the target exists relative to the
  file **or** to the project root. Root-relative is how Claude reads a path, and
  the installer's own `.claude/CLAUDE.md` link is written that way.
- Skipped: `#anchor` suffixes (the file must exist, the anchor is not checked),
  URLs, `mailto:`, anchor-only links, anything inside a code fence.

Pointers matter because hewtd link-checks only *inside* `.documentation/`.
Archive or rename a doc that a rule points at, and nothing else notices.

**Rule lines (`--map-style`):** in a `.claude/rules/` file every top-level
bullet must start `- ALWAYS` or `- NEVER` and carry a `→` pointer. In a
`CLAUDE.md`, only bullets that already have a `→` must be rules; unpointed tool
lines are allowed. Files named in `--descriptive` are exempt — by default
`operational-runbook.md`, `project-vocabulary.md` and `tool-registry.md`, which
describe rather than rule.

It is opt-in because the hook ships to every babel-fish install, and the
ALWAYS/NEVER convention is one repo's choice. On by default it would block
commits everywhere else.

## The map-style convention (for `--map-style` repos)

Everything loaded at session start is a **map**; `.documentation/` is the
source of truth.

- **Rule lines:** `ALWAYS|NEVER <the rule> — <short why> → <doc path>`. The rule
  itself stays in context — a pointer is not read before the moment a rule
  would be broken.
- **Tool / trap lines:** one or two sentences, then `→ <doc path>`.
- **Details** move word for word into `.documentation/` docs.

## How it runs

The pre-commit hook runs it when `CLAUDE.md`, `CLAUDE.local.md`,
`.claude/CLAUDE.md` or anything under `.claude/rules/` is staged. A failure
**blocks the commit** and prints the FAIL lines.

It is deliberately separate from `generate.py`, which could never do this job:

- The hook runs `generate.py` only when code files are staged — never for `.md`.
- `.claude/` is outside the watch set ([project-map-watch-set.md](../architecture/project-map-watch-set.md)).
- The hook sends `generate.py`'s errors to `/dev/null` and treats a failure as
  "skip the `git add`" — a failure there cannot block anything.

The hook block has its own `Context Check` marker. Re-running
`bash .claude/install.sh` adds it to a hook that already has the Codebase
Mapper block from an older install.

```bash
python .claude/project-map/context-check.py                  # what the hook runs
python .claude/project-map/context-check.py --budget 80000 --map-style
python .claude/project-map/context-check.py --warn-only      # report, always exit 0
python .claude/project-map/context-check.py --project-root ../other-repo
```

To change what the hook enforces, add the flags to the `context-check.py`
call in `.githooks/pre-commit`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Commit blocked` after editing a rules file | a FAIL line above it | fix the file, or add `--budget N` to the hook call |
| Rules edit committed, nothing checked | hook not running | `git config core.hooksPath` must print `.githooks`; run `bash .githooks/install.sh`. Also check `ls -l .githooks/pre-commit` is executable — git skips non-executable hooks silently |
| Existing install has no Context Check block | hook predates 2.5.0 | re-run `bash .claude/install.sh` |
| A pointer "does not exist" but the file is there | pointer is written relative to some other directory | write it root-relative, or relative to the file containing it |
| Example path in docs flagged | it is outside a code fence | put examples in a ``` fence |

Until 2.5.0 both `.githooks/` files were committed as `100644`, so no clone of
this repo ever ran its pre-commit hook. `test_hooks_are_committed_executable`
now guards that.

## Tests

`.claude/project-map/test_context_check.py` (part of `npm test`). Each check is
proven to catch a seeded bad input, not only to pass a good one. It also covers
the hook end to end (a bad commit in a temp repo is blocked), the committed hook
modes, and that the installer writes the same hook block as `.githooks/pre-commit`.
