---
title: A publish token without 2FA bypass fails with EOTP
tier: fact
domains:
  - devops
status: active
last_updated: 2026-10-28
id: npm-publish-token-needs-2fa-bypass
confidence: high
last_verified: 2026-10-28
verify_command: |
  cd "$(git rev-parse --show-toplevel)" && node -e 'process.exit(require("./package.json").publishConfig ? 0 : 1)'
provenance:
  - 2.9.0 release, 2026-10-28 (first token failed EOTP, a bypass-2FA token published)
sources:
  - package.json
tags:
  - gotcha
  - release
  - npm
invalidated_by:
  - the npm account stops requiring 2FA for publishes
---

# A publish token without 2FA bypass fails with EOTP

## Claim
The npm account requires 2FA to publish. A token without "Bypass two-factor
authentication" logs in (`npm whoami` works) and then fails `npm publish` with
`EOTP`, asking for `--otp=<code>`. An expired or revoked token fails earlier, with
`401` on `whoami` and `404` on publish.

## Instead
Publish with a short-lived granular access token, scoped to
`@theglitchking/babel-fish`, with publish rights and "Bypass two-factor
authentication" on. Pass it through a temporary `--userconfig` file that reads
`${NPM_TOKEN}` from the environment, delete the file afterwards, never print the
token, and never write it to `~/.npmrc`. Revoke the token after the release.

## How to verify
Not machine-checkable (it depends on the account's settings); the command only
checks `package.json` still carries `publishConfig`. Re-verify on the next release.
