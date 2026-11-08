---
title: A whole-tree rglob in generate.py reads every gitignored cache; scans must start from repo_files()
tier: fact
domains:
  - architecture
status: active
last_updated: 2026-11-07
id: whole-tree-rglob-reads-gitignored-caches
confidence: high
last_verified: 2026-11-07
purpose: Why did map regeneration get slow on a repo with large ignored caches?
symptoms:
  - "generate.py --force takes over a minute"
  - "pre-commit hook regenerating the project map is slow"
  - "specificity keeps generic words like feature, backend, active"
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && ! grep -n "PROJECT_ROOT.rglob\|d.rglob" .claude/project-map/generate.py && python3 .claude/project-map/test_generate.py | grep -q "ok   test_repo_files_skips_gitignored_files"
provenance:
  - issue #43 (reporter's FastAPI + React repo, cProfile), reproduced 2026-11-07 on a synthetic repo
sources:
  - .claude/project-map/generate.py
  - .claude/project-map/test_generate.py
tags:
  - gotcha
  - performance
  - project-map
invalidated_by:
  - repo_files() is removed, or generate.py stops reading file contents for specificity
---

# A whole-tree rglob in generate.py reads every gitignored cache; scans must start from repo_files()

## Claim
`PROJECT_ROOT.rglob(...)` followed by an `IGNORE_DIRS` filter still visits every
file. `IGNORE_DIRS` names only a few directories and knows nothing about
`.gitignore`. On the #43 reporter's repo the walk returned 94,787 files, of which
92,460 were gitignored (mypy cache, search-index JSON, coverage output). 3.0.0's
`specificity` read about 2 GB of them, taking a full regeneration from 14.8 s to
78.6 s. Specificity measured over a corpus that was 97% caches also made generic
words look rare.

Measured on a synthetic repo (2,271 tracked files plus 532 MB of ignored caches):
3.0.0 took 24.6 s, and 2.15 s after the fix.

## Instead
Start every scan from `repo_files()`. It uses
`git ls-files --cached --others --exclude-standard`, or outside git an `os.walk`
that prunes `IGNORE_DIRS` before descending. Filter that list; never `rglob`.
Use `_rel()` for relative paths and a string prefix test for "under this dir":
`Path.relative_to()` and `d in f.parents` on every repo file cost more than the
walk itself (5 s on the synthetic repo). Don't cache the list across calls,
because callers change files between calls.

## How to verify
The verify command fails if `generate.py` gains a whole-tree `rglob` again, or
if the test that a gitignored file is never listed stops passing.
