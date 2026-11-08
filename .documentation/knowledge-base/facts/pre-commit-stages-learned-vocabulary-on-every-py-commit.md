---
title: The pre-commit hook stages learned-vocabulary.json on every commit that touches a .py file
tier: fact
domains:
  - devops
status: active
last_updated: 2026-11-07
id: pre-commit-stages-learned-vocabulary-on-every-py-commit
confidence: high
last_verified: 2026-11-07
purpose: Why did my commit include learned-vocabulary.json changes I never meant to commit?
symptoms:
  - "commit contains .claude/project-map/learned-vocabulary.json changes I did not stage"
  - "[generate] ✓ No changes detected — skipping regeneration"
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && grep -q 'learned-vocabulary.json' .githooks/pre-commit
provenance:
  - observed while fixing issue #38 (PR #39), 2026-11-07
sources:
  - .githooks/pre-commit
  - .claude/project-map/generate.py
tags:
  - gotcha
  - project-map
  - git-hooks
invalidated_by:
  - the hook stops adding learned-vocabulary.json, or adds files only when generate.py actually regenerated
---

# The pre-commit hook stages learned-vocabulary.json on every commit that touches a .py file

## Claim
When a staged file matches the hook's source pattern (`.py`, `.ts`, `.go`, …),
`.githooks/pre-commit` runs `generate.py` and, if it exits 0, runs `git add` on
the map outputs **and** `.claude/project-map/learned-vocabulary.json`.
`generate.py` also exits 0 when it skips with "No changes detected", so any
uncommitted local change to `learned-vocabulary.json` (the session miner writes
it as you work) is swept into the commit, whatever you staged by name.

## Instead
To keep a local learned vocabulary out of a commit, set it aside around the
commit and restore it afterwards:

```bash
git stash push -m "local learned vocab" -- .claude/project-map/learned-vocabulary.json
git commit ...
git stash pop
```

Check `git show --stat HEAD` after any commit that touches a `.py` file.

## How to verify
The verify command confirms the hook still names `learned-vocabulary.json` in
its `git add` list. If it fails, this fact is stale.
