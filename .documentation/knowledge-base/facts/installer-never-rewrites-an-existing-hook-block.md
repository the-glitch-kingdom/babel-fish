---
title: Re-running the installer never rewrites a hook block that already exists
tier: fact
domains:
  - devops
status: active
last_updated: 2026-10-23
id: installer-never-rewrites-an-existing-hook-block
confidence: high
last_verified: 2026-10-23
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && python3 .claude/project-map/test_structure_check.py | grep -q 'ok   test_installer_writes_the_same_hook_block'
provenance:
  - issue #29, reproduced in the-glitch-kingdom/persistent-planning on 2026-10-23
sources:
  - .claude/install.sh
  - .githooks/pre-commit
tags:
  - gotcha
  - hooks
  - installer
invalidated_by:
  - _install_git_hooks() starts replacing whole blocks between their markers
---

# Re-running the installer never rewrites a hook block that already exists

## Claim
`_install_git_hooks()` appends each pre-commit block only when its marker
(`Codebase Mapper`, `Context Check`, `Structure Check`) is missing. A hook that
already has the block keeps its old body forever. Editing the snippet in
`install.sh` fixes new installs only; every installed repo keeps the bug. On top of
that, this repo's own `.githooks/pre-commit` is a separate copy, so a fix made there
never reached `install.sh` at all: the glossary `git add` lived only here from
`84c1120` until #29.

## Instead
Change a hook block in **both** `.githooks/pre-commit` and the snippet in
`install.sh` (`test_installer_writes_the_same_hook_block` compares them). If
installed repos need the change, add an explicit upgrade step for hooks that have
the marker but not the new content, as the glossary line does, plus a test that
installs over an old-style hook twice.

## How to verify
The verify command checks that both copies of the Codebase Mapper and Structure
Check blocks match. `test_installer_upgrades_a_hook_that_never_staged_the_glossary`
covers the upgrade step.
