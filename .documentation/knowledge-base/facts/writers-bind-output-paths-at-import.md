---
title: Map writers bind their output paths at import; only configure_paths() moves them
tier: fact
domains:
  - testing
status: active
last_updated: 2026-10-28
id: writers-bind-output-paths-at-import
confidence: high
last_verified: 2026-10-28
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && ! grep -nE '^\s*[a-z_]+\.PROJECT_ROOT\s*=' .claude/project-map/test_generate.py .claude/project-map/test_mine_sessions.py
provenance:
  - issue #18; operational-runbook.md (moved here 2026-10-28)
sources:
  - .claude/project-map/generate.py
  - .claude/project-map/mine-sessions.py
  - .claude/project-map/test_generate.py
  - .claude/project-map/test_mine_sessions.py
tags:
  - gotcha
  - testing
  - project-map
invalidated_by:
  - generate.py and mine-sessions.py resolve output paths per call instead of at import
---

# Map writers bind their output paths at import; only configure_paths() moves them

## Claim
`generate.py` and `mine-sessions.py` set `MAP_DIR`, `SECTIONS_DIR`, `CHECKSUMS`,
`LEARNED_VOC` and `GLOSSARY` from `__file__` at import time and rebind them only
inside `configure_paths()`. Setting `PROJECT_ROOT` alone leaves every write aimed
at the real repo while the caller believes it is in a temp fixture. Until #18,
`npm test` rewrote the real `glossary.json` with fixture data (10 entries down to
1 mid-release) and every test still passed.

## Instead
A test that calls a writer loads the module with `configure_paths(fixture_root)`,
never `mod.PROJECT_ROOT = fixture_root`, and `git status` is checked after the
suite. `test_grader.py` is the exception: its loader assigns a map dir, not a
project root.

## How to verify
The verify command fails if either writer's test suite assigns `PROJECT_ROOT`
directly.
