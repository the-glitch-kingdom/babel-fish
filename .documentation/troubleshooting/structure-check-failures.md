---
title: Structure check failures
tier: guide
domains:
  - troubleshooting
audience:
  - all
tags:
  - structure
status: active
last_updated: 2026-09-30
version: 1.0.0
purpose: Symptom-cause-fix for structure-check.py -- blocked commits, a check that never runs, unusable manifests, surprising detection
---

# Structure check failures

Every FAIL line printed by `structure-check.py` is followed by a `fix:` line. Start
there. This page covers what the fix line can't: the check not running, the manifest
itself failing, and results that look wrong. The rules are in the
[repo structure check](../standards/repo-structure-check.md) reference.

## "[structure-check] Commit blocked"

| FAIL says | Cause | Fix |
|---|---|---|
| `under no manifest folder` | A new top-level folder, or a file at a path no `[[folder]]` covers | Move the file, or add a `[[folder]]` (ask first: that's a structure change) |
| `root file not in root_files` | A new file at the repo root | Add it to `root_files`, or move it into a folder |
| `doesn't match … holds` | The folder doesn't take this kind of file | Put it where that kind of file lives, or widen `holds` |
| `new file in deprecated folder` | The folder is being retired | Put it where the folder's replacement lives |
| `secrets file is tracked` | A real `.env` (or `.env.prod`, `prod.env`) is in the index | `git rm --cached <file>`, keep the values out of git, and commit `.env.example`. If it's a committed test fixture with no real secrets (a vendored `.env.testing` or `.env.ci`), list its **exact path** in `exceptions`. A glob never allows a secrets file. |
| `environment 'x' is not declared` | `<env_root>/x/` exists with no `[[environment]]` | Declare it, or fold its files into a declared environment |
| `missing: stg mirrors prod` | A file exists in one environment and not the other | Add it to both, or remove it from both |
| `local-only file in cloud environment` / `deploy config in local environment` | Seeds, certs or Compose under stg/prod, or Terraform/k8s under dev | Move it to the right environment |
| `identical copy of <path>` | An environment file matches a shared file byte for byte | Delete the copy and reference the shared file |
| `per-environment migration` | Migrations split by environment | One migrations folder, applied the same way everywhere |
| `per-environment folder outside env_roots` | e.g. `apps/api/env/prod/` | Move it to `infra/env/prod/`, or add its parent to `env_roots` |

An old violation you can't fix yet belongs in `exceptions`, not in a widened `holds`.
That keeps it visible as backlog.

## The check never runs

| Symptom | Cause | Fix |
|---|---|---|
| Nothing printed on commit | No `.claude/structure.toml`. It's opt-in. | `--bootstrap`, or ask Claude to set up the repo structure |
| Nothing printed, manifest exists | `core.hooksPath` unset: git skips the hook silently | `bash .githooks/install.sh`, then `git config core.hooksPath` should print `.githooks` |
| Nothing printed, hooks installed | The hook predates 2.6.0 and has no `Structure Check` block | Re-run `bash .claude/install.sh` (or `npx @theglitchking/babel-fish init`). It appends the missing block. |
| `WARN structure-check skipped … needs Python 3.11+` | No `tomllib` before 3.11. It warns and passes on purpose. | Use Python 3.11+ locally. CI on 3.11+ still enforces. |
| Blocked locally, passes in CI (or the reverse) | The `deprecated` rule only fires on *new* files: `--staged` locally, `--since REF` in CI. Without `--since`, CI never flags it. | Run CI with `--since origin/<base>` and `fetch-depth: 0` |

## The manifest itself fails (exit 2)

The check refuses to run on a manifest it can't trust. It prints each problem, for
example: invalid TOML, an unknown `mode` / `status` / `target`, a folder listed
twice, an environment pointing at one that isn't declared, a `promotes_to` cycle, or
a `[[repo]]` with neither `path` nor `url`. Fix the named line.

Exit 2 also means "not a git repository". The check reads the git index.

## Results that look wrong

- **`--detect` says multi-repo, but this repo stands alone.** Any sibling git repo in
  the parent folder counts. Sibling detection is a fact, not a judgment. Set `mode`
  yourself; babel-fish itself uses `single` for this reason.
- **`--bootstrap` wrote into the wrong repo.** The script checks the repo it is
  installed in, not the current directory. Pass `--project-root PATH` when running
  another repo's copy.
- **`exception no longer needed`** is progress. The violation it allowed is gone, so
  delete the entry.
- **`planned folder now has files`**: flip it to `status = "active"`.
- **A file I edited isn't reported as "new".** Only additions (renames included) are
  new. Existing files in a deprecated folder pass while they move out.
