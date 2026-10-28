---
title: A release bumps package.json, plugin.json and marketplace.json together
tier: fact
domains:
  - devops
status: active
last_updated: 2026-10-28
id: releases-bump-three-manifests
confidence: high
last_verified: 2026-10-28
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && node -e 'const m=require("./.claude-plugin/marketplace.json");const v=[require("./package.json").version,require("./.claude-plugin/plugin.json").version,m.metadata&&m.metadata.version,...m.plugins.map(p=>p.version)].filter(Boolean);process.exit(new Set(v).size===1?0:1)'
provenance:
  - babel-fish 2.0.3; operational-runbook.md (moved here 2026-10-28)
sources:
  - package.json
  - .claude-plugin/plugin.json
  - .claude-plugin/marketplace.json
tags:
  - gotcha
  - release
invalidated_by:
  - Claude Code reads the plugin version from package.json alone
---

# A release bumps package.json, plugin.json and marketplace.json together

## Claim
`package.json`, `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
(twice: `metadata` and the plugin entry) all carry the version. The 2.0.2 npm
payload shipped with `plugin.json` still at 2.0.0, so Claude Code read the
installed plugin as 2.0.0 and `claude plugin update` never advanced; 2.0.3 exists
only to fix that.

## Instead
Bump every version field in the same release commit, and date the CHANGELOG entry.

## How to verify
The verify command exits non-zero when the version fields disagree.
