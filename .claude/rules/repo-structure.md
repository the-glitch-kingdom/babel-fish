# babel-fish — Repo Structure

> Auto-loaded every session. Written once by the babel-fish installer and never overwritten:
> edit it to fit this repo.

## Hard rules

1. **Decide where a file belongs before creating it.** If `.claude/structure.toml` exists, it is
   the approved layout: each `[[folder]]` says what it holds. Put the file there; the pre-commit
   hook and CI block anything outside it. To add, move or retire a folder, change the manifest
   first (the `structure-bootstrap` skill does this).
2. **No `.claude/structure.toml` yet? Suggest one** the first time a change adds a top-level folder
   or a new kind of file (an app, a service, a compose, env or deploy file):
   `python .claude/project-map/structure-check.py --detect` reads the repo, then the
   `structure-bootstrap` skill writes the manifest. Ask before creating it.
3. **Until then, keep the repo's existing layout**, and put anything it has no place for where the
   default layout does:

   | Folder | Holds |
   |--------|-------|
   | `src/` | Application source (a monorepo uses `apps/<name>/` and `packages/<name>/`) |
   | `tests/` | Tests |
   | `scripts/` | Developer and ops scripts |
   | `migrations/` | Database migrations, one folder for every environment |
   | `infra/compose/` | Compose files: `base.yml`, `dev.yml`, `remote.yml` |
   | `infra/docker/<service>/` | Entrypoint and init scripts, mounted config and certs, per-service Dockerfiles |
   | `infra/deploy/` | Cloud deploy config: `base/` shared, `<env>/` only what differs |
   | `.github/` | CI workflows |

   Env files stay where the secrets rule puts them: the root `.env` until a manifest's `env_file`
   moves them (the layouts use `infra/env/`).
4. **NEVER add a catch-all folder** (`utils/`, `misc/`, `new/`, `temp/`, `old/`). Name a
   folder for what it holds; scratch output goes in a gitignored path.
