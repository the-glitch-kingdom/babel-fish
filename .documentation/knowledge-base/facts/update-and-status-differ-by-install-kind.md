---
title: update and status behave differently for an npm install and a plugin install
tier: fact
domains:
  - devops
status: active
last_updated: 2026-10-28
id: update-and-status-differ-by-install-kind
confidence: high
last_verified: 2026-10-28
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && grep -qE '"@theglitchking/claude-plugin-runtime": "\^0\.(1\.[1-9]|[2-9])' package.json
provenance:
  - issue #17; operational-runbook.md (moved here 2026-10-28)
sources:
  - bin/babel-fish.js
  - package.json
  - hooks/hooks.json
tags:
  - gotcha
  - installer
  - plugin
invalidated_by:
  - resolveInstall() in claude-plugin-runtime stops distinguishing the two install kinds
---

# update and status behave differently for an npm install and a plugin install

## Claim
babel-fish installs as an npm project dependency (`node_modules/`), which
`update` can update, or as a Claude Code plugin (`~/.claude/plugins/cache/`),
which only `/plugin` can; there `update` says so and exits 1. Both are resolved by
`resolveInstall()` in `@theglitchking/claude-plugin-runtime`. Before 0.1.1 it
ignored `~/.claude/plugins/installed_plugins.json`, so a plugin install reported
`(not installed)`, ran a no-op `npm update` and exited 0 (#17).

## Instead
- `update` or `status` reporting `(not installed)` against a working CLI: check
  the runtime version first (needs 0.1.1 or later).
- Tests and scripts that shell out to `update` or `status` override `$HOME`, or
  the result depends on the plugins installed on that machine.
- A marketplace plugin registers its SessionStart hook in its own
  `hooks/hooks.json`; an empty `.claude/settings.json` is not evidence it is missing.

## How to verify
The verify command checks `package.json` requires the runtime at 0.1.1 or later.
