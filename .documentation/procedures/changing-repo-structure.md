---
title: Changing repo structure
tier: guide
domains:
  - procedures
audience:
  - all
tags:
  - structure
status: active
last_updated: 2026-09-30
version: 1.0.0
purpose: How to adopt the structure check, and recipes for adding, moving and retiring folders, apps, environments and repo pointers
---

# Changing repo structure

Every structural change is an edit to `.claude/structure.toml`, committed together
with the files it covers. The schema and rules are in the
[repo structure check](../standards/repo-structure-check.md) reference.

The easy path for all of this is to ask Claude to "set up the repo structure" or
"retire the legacy folder". That loads the `structure-bootstrap` skill, which follows
these same steps and asks only what it can't infer.

## Adopt it on an existing repo

1. **Get the facts:**
   `python .claude/project-map/structure-check.py --detect`.
   Confirm the mode it guessed. Sibling repos make it guess `multi-repo` even when
   they're unrelated.
2. **Write a baseline that blocks nothing:**
   `python .claude/project-map/structure-check.py --bootstrap --layout <mode>`,
   or plain `--bootstrap` when the repo matches no layout.
3. **Refine it:**
   - Replace every `TODO` purpose.
   - Tighten `holds` from what each folder really contains.
   - Declare the environments `--detect` saw.
   - Keep what already exists; the existing structure wins.
4. **Run the check.** For each FAIL on an existing file, either widen `holds` (the
   manifest was wrong) or add the path to `exceptions` (the file is wrong). The
   `exceptions` list is your cleanup backlog. A tracked `.env` can't be excepted;
   `git rm --cached` it.
5. **Wire it up:**
   - `git config core.hooksPath` should print `.githooks`. If not, run
     `bash .githooks/install.sh`.
   - `.githooks/pre-commit` should contain `Structure Check`. If not, re-run
     `npx @theglitchking/babel-fish init`.
   - Add the CI step from the reference.
   - Commit the manifest.

## Start a new repo

Either pick a mode (`--bootstrap --layout single|monorepo|multi-repo`), where every
folder starts `planned`, or describe the project to the skill:

- **Describe:** the apps, datastores, deploy target and environments.
- **Get:** a manifest where every folder is `planned`, meaning approved before it
  exists.

The check warns when a planned folder gets its first files. Flip it to `active`.

## Recipes

| Change | Steps |
|---|---|
| **Add a folder** | Add a `[[folder]]` with a `purpose` (and `holds`). Use `status = "planned"` if it doesn't exist yet, `active` once it has files. |
| **Add an app** (monorepo) | Create `apps/<name>/`. `apps` holds `*/**`, so nothing else changes. The app's environment config goes in `infra/env/<env>/`, never `apps/<name>/env/`. |
| **Add an environment** | Add an `[[environment]]` with `target` and `promotes_to`, plus `mirrors` if it must match another. Create `<env_root>/<name>/` holding only what differs. If it mirrors, give it the same file set. |
| **Move files** | `git mv`, then adjust `holds` or folders in the same commit. A new path inside a `deprecated` folder is blocked. |
| **Retire a folder** | 1. Set `status = "deprecated"`: new files are blocked. 2. Move the contents out, over as many commits as needed. 3. When the check warns it's empty, remove the `[[folder]]` entry and the folder **in one commit**. Git history keeps both. |
| **Shrink the baseline** | Fix a file listed in `exceptions`. The check then warns the entry no longer allows anything; delete it. |
| **Point at another repo** | Add a `[[repo]]` with `name`, `path` and/or `url`, and `purpose`. Set up that repo's own manifest *in that repo*. Nothing here reaches into it. |

## Rules file and procedure doc for a repo

The `structure-bootstrap` skill can write a short `.claude/rules/repo-structure.md`
and a copy of this procedure for a repo. It does so only when you ask, when you
don't know your options, or when the repo is new, and it never overwrites an
existing file.
