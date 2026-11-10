---
paths:
  - "**/*.{py,ts,tsx,js,jsx,mjs,cjs,go,rs,java,kt,rb,php,cs,swift,sh}"
---

# babel-fish — Code Hygiene

> Written once by babel-fish; yours to edit.

1. **Remove dead code in the change that makes it dead**: unused functions, imports, files, flags
   and config keys, commented-out blocks, unreachable branches. Git history keeps it.
2. **Delete implementation scaffolding before committing**: debug prints and logging, repro
   scripts, one-off harnesses, scratch files, and tests written only to get something working.
3. **Dead code you didn't create** (e.g. `.claude/project-map/sections/18-dead-code.md`): check its
   callers, then propose deleting it. Never delete it unasked inside an unrelated change.
