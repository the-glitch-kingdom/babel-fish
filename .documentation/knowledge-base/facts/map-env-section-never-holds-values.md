---
title: The project map's env section must never hold values, only names
tier: fact
domains:
  - security
status: active
last_updated: 2026-10-22
id: map-env-section-never-holds-values
confidence: high
last_verified: 2026-10-22
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && python3 .claude/project-map/test_generate.py | grep -q 'ok   test_no_secret_reaches_any_output'
provenance:
  - CHANGELOG.md (Unreleased, Security), reproduced 2026-10-22 on a scratch fixture
sources:
  - .claude/project-map/generate.py
  - .claude/project-map/grader.py
tags:
  - gotcha
  - security
  - project-map
invalidated_by:
  - section 03 starts emitting values again, or a map write path bypasses redact_secrets()
---

# The project map's env section must never hold values, only names

## Claim
Filtering `.env` values by key name leaks secrets: `DATABASE_URL`, `*_DSN` and
`*_WEBHOOK_URL` carry credentials under keys that look harmless. Through 2.6.0
`generate.py` did exactly that from the real `.env`, `redact_secrets()` was defined
but never called, and the grader's `key=value` regex could not see a markdown table
cell, so a map with five live secrets in it scored 100% on Secret Safety.

## Instead
Section 03 lists variable **names** only, from env files and from the code that
reads them, and every map write goes through `redact_secrets()` (`write_section()`,
`PROJECT_MAP.md`, glossary fields). A new output path must route through it too.
The grader carries the same pattern, so a grader hit means a write bypassed
redaction: fix the path, don't loosen the pattern.

## How to verify
`test_no_secret_reaches_any_output` plants a credential-bearing `DATABASE_URL`, a
Sentry DSN, a Slack webhook, a Stripe key and an nginx `proxy_pass` with a password,
runs a full generation and asserts none of them appears in any output file.

## Consequences
Regenerating removes a leaked value from the map but not from git history. Any
secret that was ever committed in a map section must be rotated.
