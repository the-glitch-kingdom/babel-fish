---
title: Raising a shared plugin dependency needs a floor bump and a republish
tier: fact
domains:
  - devops
status: active
last_updated: 2026-10-28
id: shared-dep-fix-needs-a-floor-bump
confidence: high
last_verified: 2026-10-28
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && grep -qx 'package-lock.json' .gitignore
provenance:
  - babel-fish 2.4.2 and persistent-planning 3.4.2; operational-runbook.md (moved here 2026-10-28)
sources:
  - package.json
  - .gitignore
tags:
  - gotcha
  - release
  - dependencies
invalidated_by:
  - the sibling plugins stop sharing one lockfile under ~/.claude/plugins/npm-cache/
---

# Raising a shared plugin dependency needs a floor bump and a republish

## Claim
The sibling plugins resolve `@theglitchking/claude-plugin-runtime` from one shared
tree at `~/.claude/plugins/npm-cache/`, whose lockfile pins one version for all of
them. Publishing a fixed runtime (0.1.1) reaches none of them: the locked 0.1.0
still satisfies `^0.1.0`.

## Instead
Raise the floor in each plugin's own `package.json` (`^0.1.1`) and republish the
plugin; that invalidates the lock entry. babel-fish 2.4.2 and persistent-planning
3.4.2 exist for this reason alone. This repo gitignores `package-lock.json`, so
the range in `package.json` is its only control.

## How to verify
The verify command checks `package-lock.json` is still gitignored here.
