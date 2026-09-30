---
title: Repo structure check
tier: standard
domains:
  - standards
audience:
  - all
tags:
  - python
  - structure
status: active
last_updated: 2026-09-30
version: 1.0.0
purpose: Reference for .claude/structure.toml and structure-check.py -- folders, lifecycle, environments, repo pointers, CLI, hook and CI
---

# Repo structure check

The project map describes where things **are**. `.claude/structure.toml` says where
things **should go**, and `.claude/project-map/structure-check.py` enforces it at
commit time and in CI. Added in 2.6.0 for
[#22](https://github.com/the-glitch-kingdom/babel-fish/issues/22).

It is **opt-in**. With no manifest the script explains the options and exits 0, and
the pre-commit hook skips it.

It checks **where files live**, not what's inside them. It will catch a Compose file
outside `infra/compose/`. It won't catch a function in the wrong module.

## The manifest

TOML, read with the standard library (`tomllib`). It is the repo's own data:
`install.sh`, `update` and `relink` never write it, and `--bootstrap` refuses to
overwrite it.

### Top-level keys

| Key | Default | Meaning |
|---|---|---|
| `mode` | `single` | `single` (flat), `monorepo` (`apps/<name>/`, `packages/<name>/`), or `multi-repo` (one of several repos; see `[[repo]]`) |
| `root_files` | `[]` | Globs allowed directly at the repo root |
| `exceptions` | `[]` | The adoption baseline: globs of known violations allowed until fixed. Only *new* violations block. |
| `env_roots` | `["infra/env", "infra/deploy"]` | Where environment folders live: `<env_root>/<env name>/` |

### `[[folder]]`

| Field | Required | Meaning |
|---|---|---|
| `path` | yes | Folder path from the repo root. Nested folders are allowed; the deepest one owns a file. |
| `purpose` | no | One line: what belongs here. Shown to agents via the map pointer and the skill. |
| `holds` | no | Globs relative to `path` (`*` stops at `/`, `**` crosses it). Omit to allow anything. |
| `status` | no (`active`) | `planned` / `active` / `deprecated` (see lifecycle below) |
| `added` | no | Date, for the record |

### `[[environment]]`

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | e.g. `dev`, `stg`, `prod`. The folder name under each env root. |
| `target` | yes | `local` (localhost) or `cloud` |
| `promotes_to` | no | The next environment. Must be declared; cycles are rejected. |
| `mirrors` | no | This environment must hold the same files as that one (stg → prod) |

### `[[repo]]` (multi-repo)

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The other repo's name |
| `path` | one of path/url | Local checkout, relative to this repo. Warns if it isn't a git repo. |
| `url` | one of path/url | Remote |
| `purpose` | no | What it is to this repo |

A pointer is only a record. Each pointed-to repo runs its own babel-fish (map, drift,
structure check), and nothing crosses repos: no inheritance, no cross-repo checks.

## Folder lifecycle

| Status | Meaning | Check behavior |
|---|---|---|
| `planned` | Approved, not created yet | May be created. Warns once it has files (flip to `active`). |
| `active` | In use | Files must match `holds`. Warns if it has no files. |
| `deprecated` | Being retired | **New files fail.** Existing ones pass while they move out. Warns when empty. |
| (removed) | Entry and folder deleted in the same commit | Git history keeps it |

"New" means staged additions with `--staged` (the hook), or files added since a ref
with `--since REF` (CI). Without either flag nothing counts as new, so the deprecated
rule doesn't fire.

## Rules

| Level | Rule |
|---|---|
| FAIL | A tracked file under no manifest folder, or a root file not in `root_files` |
| FAIL | A file that doesn't match its folder's `holds` |
| FAIL | A new file in a `deprecated` folder |
| FAIL | A tracked secrets file: `.env`, `.env.<x>`, `<x>.env`. `*.example`, `.sample`, `.template` and `.dist` pass. **`exceptions` can't allow this.** |
| WARN | Lifecycle status out of date (see above) |
| WARN | An `exceptions` entry that no longer allows anything (remove it; the baseline shrinks) |
| WARN | A `[[repo]]` whose `path` isn't a git checkout |

### Environment rules (only when `[[environment]]`s are declared)

| Level | Rule | Why |
|---|---|---|
| FAIL | `<env_root>/<x>/` where `x` isn't declared (`base`, `shared`, `common` and `modules` are shared folders) | No surprise environments |
| FAIL | A `mirrors` environment holds a different file set from its target | Stg that differs from prod isn't testing prod. Dev is exempt. |
| FAIL | Local-only files (Compose, seeds, fixtures, certs) in a cloud environment | Local tooling doesn't ship |
| FAIL | Deploy config (Terraform, Kustomize, Helm, Fly, Render, Vercel, Railway) in a local environment | Local environments don't deploy |
| FAIL | An environment file byte-identical to a shared file (git blob hash; empty files excluded) | Environment folders hold deltas only |
| FAIL | A per-environment migrations folder, inside or outside the env roots | The schema has one path forward through every environment |
| FAIL | `<env\|envs\|environments\|overlays>/<declared env>/` outside `env_roots` | In a monorepo, app environment config goes in the shared env root |
| WARN | Workflow copies that differ only by environment (`deploy-stg.yml` + `deploy-prod.yml`) | Prefer one workflow that takes the environment as input |

The local-only and deploy lists are constants at the top of the script
(`LOCAL_ONLY`, `DEPLOY_ONLY`). Extend them there when a real repo needs another
platform.

## CLI

```bash
python .claude/project-map/structure-check.py                      # check (no manifest: explain the options)
python .claude/project-map/structure-check.py --staged             # check; staged adds are "new" (the hook)
python .claude/project-map/structure-check.py --since origin/main  # check; adds since REF are "new" (CI)
python .claude/project-map/structure-check.py --warn-only          # report, always exit 0
python .claude/project-map/structure-check.py --detect [--json]    # facts: mode + reasons, envs, folders, siblings
python .claude/project-map/structure-check.py --bootstrap [--layout single|monorepo|multi-repo] [--mode M]
```

Exit codes: `0` clean, no manifest, or Python < 3.11. `1` violations. `2` an unusable
manifest, or not a git repository.

`--project-root PATH` points it at another repo. Without it, the script checks the
repo it is installed in, not the current directory.

### Detection

`--detect` reports facts and never guesses a purpose:

- **monorepo:** a workspace file (`pnpm-workspace.yaml`, `turbo.json`, `nx.json`,
  `lerna.json`, `go.work`, `rush.json`, `workspaces` in `package.json`, Cargo
  `[workspace]`), or 2+ packages with their own manifest under
  `apps|packages|services|libs`
- **multi-repo:** sibling git repos in the parent folder, or `.gitmodules`
- **single:** otherwise
- **environments seen:** `.env.<x>`, `compose.<x>.yml`, `infra/compose/<x>.yml`,
  `<env dir>/<x>/`, and workflow `environment:` keys

Untracked files count (a new repo may have nothing staged). Judgment calls, such as
a folder's purpose, which layout fits, or whether siblings are related, belong to the
`structure-bootstrap` skill.

### Bootstrap and layouts

`--bootstrap` writes a starting manifest.

- **Plain:** one active folder per top-level directory, with a `TODO` purpose.
- **`--layout NAME`:** starts from `.claude/templates/structure/NAME.toml`.
  - Folders that exist become `active`, the rest `planned`.
  - Each layout declares dev (local) → stg → prod (cloud), with stg mirroring prod.

Either way, today's violations seed `exceptions`, so adopting the check blocks
nothing. Environments seen and sibling repos are added as commented-out suggestions.

The layouts use the manifest's own schema. They are references, not rules: on an
existing repo, the existing structure wins.

## Hook and CI

The pre-commit hook's `Structure Check` block runs `structure-check.py --staged` only
when `.claude/structure.toml` exists, and blocks the commit on a FAIL. `install.sh`
carries the identical block (test-guarded) and appends it to hooks installed by older
versions.

The hook can be skipped (`--no-verify`) or not installed at all (`core.hooksPath`
unset). CI is the enforcement that can't be skipped:

```yaml
- uses: actions/checkout@v4
  with: { fetch-depth: 0 }
- uses: actions/setup-python@v5
  with: { python-version: "3.12" }
- run: python .claude/project-map/structure-check.py --since origin/${{ github.base_ref || 'main' }}
```

## Python version

Only this script needs Python 3.11+ (for `tomllib`). The rest of babel-fish keeps
3.8. On an older Python it prints a readable warning (what was skipped, why, how to
fix it) and exits 0, so it never blocks. `--detect` and plain `--bootstrap` still
work there.

## In the project map

When a manifest exists, `PROJECT_MAP.md` gets a **Repo Structure** section. It holds
a one-line pointer to the manifest (never a copy) and lists the related repos. Every
session sees where the rules live without an extra rules file.

## Why a separate script

This is the same reason as the [auto-loaded context check](auto-loaded-context-check.md):
the hook runs `generate.py` only when code is staged and discards its errors, so a
check inside it could never block a commit.

## See also

- [Changing repo structure](../procedures/changing-repo-structure.md): adopting the
  check, and the recipes for adding and retiring folders, apps and environments
- [Structure check failures](../troubleshooting/structure-check-failures.md)
- `skills/structure-bootstrap/SKILL.md`: the skill that does the judgment calls
