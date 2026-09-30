---
name: structure-bootstrap
description: |
  Set up, adopt or change a repo's structure manifest (.claude/structure.toml) — the
  approved folders, what each may hold, their lifecycle (planned / active / deprecated),
  the dev → stg → prod environments and pointers to related repos — enforced by
  babel-fish's structure-check.py at commit time and in CI.
  Use when the user asks to set up / plan / detect / adopt the repo structure or folder
  layout, asks where a new file, app, service or environment should go, wants to add,
  move or retire a folder, starts a brand-new repo or project, or hits a
  "[structure-check] Commit blocked" failure.
---

# Repo structure: set up, adopt, change

`.claude/structure.toml` says where files go. `.claude/project-map/structure-check.py`
enforces it: pre-commit (only when the manifest exists) and CI. The script gathers
**facts** and checks **placement**. You make the **judgment calls**: what a folder is
for, which layout fits, what to ask.

## Ground rules

- **The manifest is the repo's data.** Never overwrite one. Change an existing manifest
  only by editing it, and only after the user agrees to the change.
- **Existing structure wins.** On an existing repo a layout template is a reference.
  Its differences become questions for the user, or `exceptions`, never a block.
- **Ask only what you can't infer.** Read the tree first. Ask about purpose only when
  the contents don't answer it.
- **One repo at a time.** For multi-repo, record `[[repo]]` pointers. Never write into
  another repo. Each one runs its own babel-fish (map, drift, structure check).
- **Placement, not contents.** The check can say a Compose file is in the wrong
  folder. It can't say a function is in the wrong file.

If `.claude/project-map/structure-check.py` is missing, the repo hasn't run the full
installer: `npx @theglitchking/babel-fish init`.

Commands below use `python3`. Many machines have no `python`. Reading a manifest
needs 3.11+; on older versions the check warns and passes, which proves nothing.

**`holds` globs** are relative to the folder's `path`. `*` and `?` stop at `/`; `**`
crosses it; `**/` may match zero directories, so `**/*.py` also matches direct
children. Name extensionless files literally (`"pre-commit"`, `"Makefile"`).

## Step 0: facts

```bash
python3 .claude/project-map/structure-check.py --detect --json
```

Returns `mode` + `reasons`, `environments` (name → evidence paths), `top_level`
(folders, file counts, main extensions), `root_files`, `sibling_repos`, `packages`,
`near_empty`, `manifest` (exists?) and `layouts` (available templates in
`.claude/templates/structure/`). Needs Python 3.11+ only to *read* a manifest;
`--detect` works on any version.

Then pick the flow:

| Situation | Flow |
|---|---|
| `manifest` is true | **D: change the structure** |
| `near_empty` is true | **B: new repo** |
| The user doesn't know what their options are | **C: options** |
| Otherwise | **A: adopt an existing repo** |

## Flow A: adopt an existing repo

1. Confirm the mode with the user in one line, using the reasons ("Looks like a
   monorepo: pnpm-workspace.yaml, apps/api + apps/web. Right?"). Siblings or
   `.gitmodules` in a monorepo still means `[[repo]]` pointers.
2. Get a baseline that blocks nothing:
   ```bash
   python3 .claude/project-map/structure-check.py --bootstrap --layout <mode>
   ```
   Top-level folders the layout doesn't cover become their own `[[folder]]` entries
   ("TODO … (not in the <mode> layout)"). Leftover violations seed `exceptions` as
   exact paths. If most of the `top_level` folders from Step 0 aren't in the layout,
   use plain `--bootstrap` instead. It declares exactly what exists, with nothing to
   prune.
3. Refine `.claude/structure.toml` from what is actually there:
   - **Prune what the layout brought:**
     - `planned` folders this repo won't have, e.g. a top-level `migrations` when
       migrations already live in `db/`
     - the layout's dev/stg/prod `[[environment]]` blocks if Step 0 found no
       environments. Ask first if the user may be planning them.
   - **purpose:** one line per folder, from its README or a few of its files. Check
     the purposes the layout supplied too, not just the `TODO`s; they're generic
     and can be wrong for this repo.
   - **holds:** tight enough to catch drift, loose enough not to nag. Survey the
     real contents (`git ls-files <folder> | sed 's/.*\.//' | sort | uniq -c`).
     `--detect` lists only the top few extensions per folder, and holds built from
     that alone will FAIL on the rest. E.g. `["**/*.py"]` for a Python package,
     `["*/.env.example"]` for `infra/env`. Leave `holds` out for folders that
     legitimately hold anything.
   - **environments:** from `environments` in the facts. Targets: `dev` / `local` →
     `local`, everything else → `cloud`. Ask if a name is ambiguous (`test`, `qa`).
     Order: `promotes_to` dev → stg → prod. `mirrors = "prod"` on stg when both exist.
     `env_roots` if env folders live somewhere other than `infra/env` and `infra/deploy`
     (e.g. `k8s/overlays`).
   - **root_files:** keep what's there; globs for families (`*.lock`, `tsconfig*.json`).
4. Run the check:
   ```bash
   python3 .claude/project-map/structure-check.py
   ```
   Straight after bootstrap it's usually green. Tightening `holds` is what surfaces
   FAILs. Also review the `exceptions` bootstrap added: a file that legitimately
   belongs at the root (`.env.example`, `.gitleaks.toml`) goes in `root_files`, not
   the backlog. For each FAIL on a file that already exists, either widen `holds` (the manifest
   was wrong) or add the path to `exceptions` (the file is in the wrong place). Tell
   the user which ones you put in `exceptions`: that list is the cleanup backlog.
   Always use exact paths, never globs (a glob lets future files through). A tracked
   secret (`.env`): tell the user, and have them `git rm --cached` it. Add its exact
   path to `exceptions` only if the user confirms it's a committed test fixture with
   no real secrets (e.g. a vendored `.env.testing`). Never decide that yourself.
5. List what differs from the layout as suggestions, not changes. For example:
   "secrets config lives in `apps/api/config/prod.env`; the layout puts it in
   `infra/env/prod/`".
6. Wiring: `.githooks/pre-commit` should contain a `Structure Check` block (re-run
   `npx @theglitchking/babel-fish init` if not). `git config core.hooksPath` should
   print `.githooks`. If the repo has CI (`.github/workflows/`), offer the CI step
   (below): the hook can be skipped, CI can't. Commit the manifest.

## Flow B: new repo

Offer two paths:

- **Pick a mode.** Explain single / monorepo / multi-repo in one line each, then
  `--bootstrap --layout <mode>`. Every folder starts `planned`.
- **Plan it.** Ask what the project is: apps or services, datastores, where it
  deploys, which environments. Then build the manifest from the closest layout:
  - one `[[folder]]` per thing the plan needs, `status = "planned"` (approved before
    it exists; the check warns once it has files, and you flip it to `active`)
  - environments from the plan (default dev → stg → prod)
  - drop layout folders the plan doesn't need

  Show the resulting tree as a short preview and confirm before writing.

Then offer the doc templates (below). A new repo is one of their triggers.

## Flow C: options

Run the script with no flags. With no manifest it prints the modes, what detection
found and the ways to turn the check on. Summarize that in a few lines, then ask
which flow they want. Offer the doc templates too.

## Flow D: change the structure

Every change is an edit to the manifest, committed together with the files it
covers:

| Change | Recipe |
|---|---|
| **Add a folder** | New `[[folder]]` with a purpose (+ holds). `planned` if it doesn't exist yet, `active` once it has files. |
| **Add an app** (monorepo) | Create `apps/<name>/`. `apps` holds `*/**` already. Its env config goes in `infra/env/<env>/`, never `apps/<name>/env/`. |
| **Add an environment** | New `[[environment]]` (`target`, `promotes_to`; `mirrors` if it must match another). Create `<env_root>/<name>/` with only its deltas. If it mirrors, give it the same file set. |
| **Move files** | `git mv` them, then fix `holds` / folders. A new path inside a deprecated folder is blocked. |
| **Retire a folder** | 1) `status = "deprecated"`, so new files are blocked. 2) Move the contents out. 3) Once empty (the check warns), remove the `[[folder]]` entry and the folder **in the same commit**. Git history keeps it. |
| **Shrink the baseline** | Fix a file listed in `exceptions`. The check warns when an entry no longer allows anything; delete it. |
| **Point at another repo** | `[[repo]]` with `name`, `path` (local checkout) and/or `url`, `purpose`. That repo sets up its own manifest. Offer to do it there, as a separate step. |

On a `[structure-check] Commit blocked` failure, read the FAIL lines. Each has a
`fix:` line. Apply it, or change the manifest if the structure really should change,
and ask the user first.

## Doc templates: only on these triggers

Write these only when (1) the user asks for them, (2) you're in Flow C, or (3) it's a
new repo (Flow B). Never overwrite an existing file; propose a diff instead.

- **`.claude/rules/repo-structure.md`**: auto-loaded, so keep it short and in the rule
  form context-check accepts:
  ```markdown
  # Repo structure

  - ALWAYS check `.claude/structure.toml` before creating a folder or a new kind of file — it lists where things go. → `<procedure doc>`
  - NEVER create a top-level folder or a per-environment copy of a file without asking — structure-check blocks the commit. → `<procedure doc>`
  - NEVER commit a real `.env` — only `.env.example`; values live in the environment or a secret manager. → `<procedure doc>`
  ```
- **Procedure doc `changing-repo-structure.md`:** the Flow D table, rendered for this
  repo's actual mode, env_roots and environments. Where it goes:
  - If `.documentation/` exists (hit-em-with-the-docs), write it into
    `.documentation/procedures/` and run `npx hewtd integrate <file> -a`.
  - Otherwise, skip the file, point the rules file at `.claude/structure.toml`, and
    tell the user the recipes are available by asking Claude.

## CI

The pre-commit hook can be skipped (`--no-verify`) or not installed. CI is the check
that can't be skipped. It needs Python 3.11+ and the base branch fetched:

```yaml
- uses: actions/checkout@v4
  with: { fetch-depth: 0 }
- uses: actions/setup-python@v5
  with: { python-version: "3.12" }
- run: python3 .claude/project-map/structure-check.py --since origin/${{ github.base_ref || 'main' }}
```
