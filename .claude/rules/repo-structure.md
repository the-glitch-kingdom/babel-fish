# babel-fish — Repo Structure

> Written once by babel-fish; yours to edit.

1. **Decide where a file belongs before creating it.** If `.claude/structure.toml` exists, it is the
   approved layout (each `[[folder]]` says what it holds), enforced by the pre-commit hook and CI.
   To add, move or retire a folder, change the manifest first (the `structure-bootstrap` skill).
2. **No manifest yet?** The first time a change adds a top-level folder or a new kind of file (app,
   service, compose, env or deploy file), suggest one: `python .claude/project-map/structure-check.py --detect`,
   then the `structure-bootstrap` skill. Ask before creating it.
3. **Until then, keep the existing layout**, and put anything it has no place for in the default:
   `src/` (monorepo: `apps/<name>/`, `packages/<name>/`), `tests/`, `scripts/`, `migrations/`,
   `infra/compose/` for compose files, `infra/docker/<service>/` for what a container mounts or
   builds from, `infra/deploy/` for cloud config, `.github/` for CI. Env files stay where the
   secrets rule puts them.
4. **NEVER add a catch-all folder** (`utils/`, `misc/`, `new/`, `temp/`, `old/`); name it for what it holds.
