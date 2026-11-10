---
paths:
  - ".github/workflows/**"
  - ".github/actions/**"
  - "**/.gitlab-ci.yml"
  - "{.circleci,.buildkite}/**"
  - "**/{Jenkinsfile,azure-pipelines.yml,bitbucket-pipelines.yml,.travis.yml}"
---

# babel-fish — CI Pipelines

> Written once by babel-fish; yours to edit.

CI is optimized for time without giving up coverage: every check runs once, over only what it needs.

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
