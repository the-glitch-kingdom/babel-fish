# babel-fish — Git Workflow

> Written once by babel-fish; yours to edit.

1. **ALWAYS cut a branch from `main` before any change**, however small:
   `git checkout -b <type>/<short-description> main` (`feat/`, `fix/`, `docs/`, `chore/`). Never
   branch from another feature branch unless the user asks.
2. **ALWAYS start from an up-to-date `main`**, at session start and after every merge:
   `git checkout main && git fetch origin main && git merge --ff-only origin/main`
3. **Branch → commit → push the branch → PR against `main` → stop and wait.** Report
   the link. NEVER push or merge to `main`, or merge your own PR, without explicit
   permission: "commit" or "open a PR" is not permission to merge.
4. **NEVER bypass hooks** (`--no-verify`, `-n`) unless the user authorizes that commit. Fix the
   violation, or ask about debt that predates your change.
5. **NEVER force-push a shared branch** or rewrite history others may have pulled.
6. **Commits are conventional** (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`), one
   logical change each, the body says why. Stage files by name, never `git add -A`. A PR says what
   changed, why, and how it was tested, with real output.
7. **After a merge, sync `main` (rule 2), then delete the branch locally and on the remote**:
   `git branch -d <branch> && git push origin --delete <branch> && git fetch --prune`.
   Use `-d`, never `-D`: it refuses an unmerged branch. After a squash merge `-d` refuses too;
   confirm the PR is merged before using `-D`.
