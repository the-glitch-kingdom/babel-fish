---
paths:
  - "**/package.json"
  - "**/{requirements*.txt,pyproject.toml,Pipfile,setup.cfg}"
  - "**/{go.mod,Cargo.toml,Gemfile,composer.json,pom.xml,build.gradle,build.gradle.kts,*.csproj}"
  - "**/{.nvmrc,.node-version,.python-version,.tool-versions,rust-toolchain.toml}"
  - "**/Dockerfile*"
  - "**/*compose*.{yml,yaml}"
  - ".github/workflows/**"
---

# babel-fish — Dependency Versions

> Written once by babel-fish; yours to edit.

1. **ALWAYS use the latest stable version** of every package, runtime, tool, image, CI action and
   service; where an LTS line exists (Node, Java, Ubuntu, …), the newest LTS. NEVER a pre-release
   (alpha, beta, rc, nightly, canary, `next`).
2. **Look it up; never trust memory**: `npm view <pkg> version`, `pip index versions <pkg>`,
   `go list -m -versions <mod>`, or the release page.
3. **The only exception is a newer version that was tried and failed.** Pin the newest one that
   works and record it twice: a comment at the pin (what broke, the version, the date) and an entry
   under Known Issues in `.claude/rules/operational-runbook.md`. An unrecorded pin is drift: bump it.
4. **Recheck a recorded pin whenever you touch that dependency**; once the newest works, drop the
   pin, the comment and the runbook entry together.
