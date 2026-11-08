---
title: Grep and Glob tool inputs are directories and globs, not file locations
tier: fact
domains:
  - architecture
status: active
last_updated: 2026-11-07
id: grep-glob-inputs-are-not-file-locations
confidence: high
last_verified: 2026-11-07
purpose: Why did learned vocabulary point at directories, globs and files that do not exist?
symptoms:
  - "learned-vocabulary.json targets include a directory like frontend/src"
  - "glossary canonical_path is a comma-separated list"
  - "learned alias points at a file that was deleted or never existed"
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && python3 .claude/project-map/test_mine_sessions.py | grep -q "ok   test_tool_paths_are_existing_files_only"
provenance:
  - issue #38 (measured on a 1,168-entry FastAPI + React repo, 2026-11-08)
sources:
  - .claude/project-map/mine-sessions.py
  - .claude/project-map/generate.py
tags:
  - gotcha
  - project-map
  - learned-vocabulary
invalidated_by:
  - mine-sessions.py stops reading Grep/Glob tool inputs, or the tools' input schemas change
---

# Grep and Glob tool inputs are directories and globs, not file locations

## Claim
`mine-sessions.py` pairs a user phrase with every file the assistant touched in
the turn, reading `file_path`, `path` or `pattern` from Read, Edit, Write, Grep
and Glob calls. For Grep, `path` is usually a directory (`frontend/src`); for
Glob, `pattern` is a glob (`src/**/*.py`). Before #38 those were stored as
learned locations unchecked, and merges only ever added targets, so renamed and
deleted files stayed forever. In one repo 341 of 2,442 learned paths were
directories and 80 no longer existed.

## Instead
Record a tool path only when `is_repo_file()` says it is an existing file in
the repo, the same check Bash tokens get, and prune targets that stopped existing
(`prune_missing()`). `generate.py` checks again at generation time, because files
change between mining runs: `finalize_vocab()` keeps only existing files in
`paths` and directories in `dirs`.

## How to verify
The verify command runs the miner test that feeds a Grep on a directory, a Glob
pattern and a missing file, and expects no location recorded.
