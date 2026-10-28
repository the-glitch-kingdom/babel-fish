---
title: Any edit to install.sh must regenerate checksums.json
tier: fact
domains:
  - devops
status: active
last_updated: 2026-10-28
id: installer-checksum-must-match-install-sh
confidence: high
last_verified: 2026-10-28
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && python3 .claude/project-map/test_structure_check.py | grep -q 'ok   test_installer_checksum_matches_install_sh'
provenance:
  - operational-runbook.md (moved here 2026-10-28); commit a2dad3f fixed the same staleness earlier
sources:
  - checksums.json
  - install.sh
  - .claude/install.sh
tags:
  - gotcha
  - installer
  - release
invalidated_by:
  - the curl installer stops verifying checksums.json before running .claude/install.sh
---

# Any edit to install.sh must regenerate checksums.json

## Claim
The curl installer verifies the SHA256 of `.claude/install.sh` against
`checksums.json` before running it, and aborts with CHECKSUM MISMATCH when they
differ. The manifest has gone stale after an installer edit more than once
(commit `a2dad3f` fixed it before).

## Instead
In the same change as any `.claude/install.sh` edit, write the new hash into
`checksums.json` (`sha256sum .claude/install.sh`). If the documented curl
one-liner aborts, check this first.

## How to verify
`test_installer_checksum_matches_install_sh` fails whenever the two disagree.
