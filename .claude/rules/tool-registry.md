# babel-fish — Tool Registry

> Loaded every session, so it holds pointers, not detail. Written once by babel-fish; yours to edit.

## Adding a tool

Every CLI, MCP server, SDK, credential or integration this repo uses gets one **pointer record**:
its name, what it is for (plus the one trap that would mislead you, if any), and where the detail lives.

```
- **`<tool>`**: <what it is for; the trap, if any>. → `<path to the doc>`
```

1. **The detail goes in a doc**: install, version, auth, flags, examples. If the repo uses
   hit-em-with-the-docs (it has a `.documentation/` folder), write it the hewtd way: a doc in its
   domain folder (CLIs and integrations usually `devops/`), and a trap as a fact under
   `.documentation/knowledge-base/facts/` tagged `gotcha`. Then run `hewtd maintain` and add the
   pointer record here. Without hewtd, use the repo's docs folder.
2. **Update it in the same change** that adds, removes or changes a tool: its line and its doc together.
3. **NEVER write a secret here.** Name the variable, profile or secret manager that holds it.

## Tools

- **`python3`** (3.11+): runs every project-map script; below 3.11 `structure-check.py` warns and passes. → `.documentation/troubleshooting/structure-check-failures.md`
- **`node`** + `@theglitchking/claude-plugin-runtime`: the `babel-fish` CLI (`init`, `update`, `status`); npm and plugin installs update differently. → `.documentation/knowledge-base/facts/update-and-status-differ-by-install-kind.md`
- **`npm`**: `npm test` runs all suites; publishing needs a token with 2FA bypass. → `.documentation/knowledge-base/facts/npm-publish-token-needs-2fa-bypass.md`
- **`hewtd`** (hit-em-with-the-docs): manages `.documentation/`; run `hewtd maintain` after adding or editing a doc. → `.documentation/README.md`
