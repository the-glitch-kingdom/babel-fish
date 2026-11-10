# babel-fish — CI Pipelines

> Written once by babel-fish; yours to edit.

CI is optimized for time without giving up coverage: every check runs once, over only what it needs.

## Checks

1. **Read the whole pipeline before adding to it.** If a job already runs that tool, suite or scan,
   extend it (another path, rule or flag) instead of adding a job. One linter run covers every
   language it supports; one test run covers every suite.
2. **NEVER run the same scan, build, install or test twice** in one pipeline, across jobs, workflows
   or matrix entries. Build once and pass the result on as an artifact; cache dependencies by lockfile
   hash. A matrix is only for what really differs (runtime versions, OS), never to split one job.
3. **Scan what changed, not the whole repo**, when the tool can: path filters on workflows,
   changed-files or affected-only modes. Keep one full run on `main` or a schedule
   to catch what a diff misses.
4. **Fail fast**: cheap checks (lint, types) before slow tests, independent jobs in parallel,
   dependent ones chained (`needs:`), and superseded PR runs cancelled (`concurrency:` with
   `cancel-in-progress: true`).
5. **NEVER trade coverage for speed**: no dropping, skipping or `continue-on-error` on a check to
   shorten the run. Merge checks, don't remove them. A PR that changes CI says which jobs merged,
   what each still covers, and the run time before and after.

## Security scanning

1. **One tool per kind of scan**: secrets, dependencies, code (SAST), container images, IaC. Before
   adding a scanner, check what already covers that kind (including GitHub's built-in
   Dependabot and secret scanning); two tools on the same kind is a duplicate, not defense in depth.
2. **Scan each thing once, where it is cheapest**: secrets and code on the PR diff, dependencies when
   a lockfile changes, the image once after it is built (the image that ships, never a rebuild).
   A scheduled full scan catches new CVEs and history that diffs miss.
3. **New high or critical findings fail the build.** Existing ones go in the tool's baseline, and
   each suppression names its reason and an expiry. NEVER `continue-on-error`, `|| true` or a
   lowered threshold to get a scan green.

## Deployments

1. **Build once, promote the same artifact** (image digest, package version) through every
   environment. NEVER rebuild per environment; environment config comes from variables and the
   secret manager.
2. **Deploy jobs reuse the checks; they never rerun them.** Gate them with `needs:` on the jobs that
   already passed, and deploy only from `main` or a release tag.
3. **One deploy workflow, parameterized by environment**, never a copy per environment. Protect
   production with the platform's environment rules (required reviewers).
4. **Deploys queue; they are never cancelled midway**: a `concurrency:` group per environment
   with `cancel-in-progress: false`.
5. **Every deploy ends with a health check and has a rollback**: redeploy the previous artifact.
   The procedure is a pointer record under Deploy Procedures in the operational runbook.
