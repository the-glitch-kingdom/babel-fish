---
title: Scripts babel-fish installs into a repo must not contain a credential-shaped example, even in a comment
tier: fact
domains:
  - security
status: active
last_updated: 2026-11-07
id: installed-scripts-must-not-hold-credential-shaped-examples
confidence: high
last_verified: 2026-11-07
purpose: Why does a secret scanner fail the PR that updates babel-fish in a downstream repo?
symptoms:
  - "gitleaks database-url-password finding in .claude/project-map/generate.py"
  - "secret scanner flags .claude/project-map/grader.py after a babel-fish update"
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && python3 .claude/project-map/test_grader.py | grep -q 'ok   test_installed_scripts_hold_no_credential_shaped_url'
provenance:
  - issue #40, reproduced 2026-11-07 with gitleaks v8.18.4 and latest (2 findings)
sources:
  - .claude/project-map/generate.py
  - .claude/project-map/grader.py
  - .claude/project-map/test_grader.py
  - .claude/install.sh
tags:
  - gotcha
  - security
  - project-map
invalidated_by:
  - install.sh stops copying the project-map scripts into the target repo
---

# Scripts babel-fish installs into a repo must not contain a credential-shaped example, even in a comment

## Claim
`install.sh` copies `generate.py`, `grader.py`, `mine-sessions.py`,
`context-check.py` and `structure-check.py` into every repo that installs
babel-fish, where that repo's secret scanner reads them like its own code.
Scanners match text, not intent: until #40 the comment
`# URL userinfo: postgres://user:pass@, DSN keys` beside the redaction pattern
was flagged by gitleaks' common `database-url-password` rule, so the scripts that
prevent leaks failed every downstream CI secret gate. Masking the password
(`scheme://USER:***@host`) passes that rule but still matches a broader
any-scheme `user:secret@` rule.

The test files are not affected: they ship to npm but stay in `node_modules`,
which repos ignore.

## Instead
Describe the shape in words (`the user:password part before '@' in a URL`)
rather than writing an example of it. Credential-shaped fixtures belong in the
`test_*.py` files, which are never installed. The test
`test_installed_scripts_hold_no_credential_shaped_url` scans every script
`install.sh` copies with a broad URL-with-password regex.

## How to verify
The verify command runs that test.
