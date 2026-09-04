---
title: Project map is empty or stale
tier: guide
domains: [troubleshooting]
status: active
last_updated: '2026-09-04'
version: '1.0.0'
purpose: Symptom-cause-fix for an empty project map, a map that will not regenerate, and a stale section 19
---

# Project map is empty or stale

Three failures that look alike from the outside. Work down in order — the
regeneration one masks the others, because a map that never re-runs cannot show
you that a parser was fixed.

---

## "My map regenerates but every section says none detected"

**Symptom.** `PROJECT_MAP.md` reports `API Routes 0 | Data Models 0 | Schemas 0`,
Stack reads `unknown / unknown`, and `sections/` totals only a few KB of stubs.

**Cause.** Expected in a plugin or skill repository. Every code extractor is
framework-shaped — `PythonRouteParser` wants `@router.get`, `PythonModelParser`
wants a SQLAlchemy or Django base class. A repo of markdown skills, slash
commands and bash scripts has none of that, and there is no plugin-repo
equivalent of a route or a model.

**Fix.** Sections 01 (vocabulary) and 10 (tools) are the ones that should carry
the value. Confirm your manifests are where the parser looks:

```bash
ls skills/*/SKILL.md commands/*.md
python3 .claude/project-map/generate.py --force
```

Then check section 01 is not the stub:

```bash
cat .claude/project-map/sections/01-vocabulary.md
```

A skill needs a leading `---` frontmatter block to be seen at all. `name` is
optional, `description` is optional, but the block itself is required. See the
[skill parser contract](../api/skill-parser-contract.md).

Sections 04/05/06/09/13 staying empty in a plugin repo is correct, not a bug.

---

## "I edited a file and the map did not change"

**Symptom.** `generate.py` prints
`✓ No changes detected — skipping regeneration (use --force to override)`
even though you just edited a file.

**Cause.** The file is not in the watch set, so the checksum did not move. Only
watched files can trigger a regeneration — see
[project map watch set](../architecture/project-map-watch-set.md).

**Fix.** Ask the generator what it is watching:

```bash
python3 -c "
import sys, importlib.util
s = importlib.util.spec_from_file_location('g', '.claude/project-map/generate.py')
g = importlib.util.module_from_spec(s); sys.argv = ['g']; s.loader.exec_module(g)
w = g.collect_watched_files()
print(f'{len(w)} watched')
for p in w: print(' ', p.relative_to(g.PROJECT_ROOT))
"
```

If your file is absent, it is one of:

- **an extension nobody watches** → add it to `WATCHED_EXTENSIONS`
- **a manifest in a non-standard location** (e.g. `plugins/foo/commands/*.md`)
  → add a glob to `WATCHED_GLOBS`, matched against the repo-relative path
- **under a directory in `IGNORE_DIRS`** — most often `.claude`. Files there are
  parsed via direct globs but never watched, so they refresh only on the next
  run something else triggers.

`--force` always bypasses the check, and is the right answer when you just want
the map rebuilt now.

> Historically `.md` and `.sh` were both unwatched, which meant editing a
> `SKILL.md` or an `install.sh` left the checksum bit-identical. Fixed in #6.

---

## "Section 19 lists the wrong documents"

**Symptom.** Doc pointers list files that no longer exist, miss ones that do, or
are full of `INDEX.md` / `REGISTRY.md` noise.

**Cause and fix**, in order of likelihood:

| Symptom | Cause | Fix |
|---|---|---|
| A doc you added is missing | Its directory is not in `DOC_DIRS` | Add the directory |
| Docs moved and section 19 kept the old list | Path set did change — should have refreshed | `--force`; if that fixes it, the walk and the checksum have drifted |
| Body edits never refresh it | **Working as designed** | Section 19 lists paths, never content |
| Full of `INDEX.md` / `REGISTRY.md` | Skips not applied | Check `DOC_SKIP_NAMES` / `DOC_SKIP_DIRS` |

Only add, rename and delete move the checksum. Editing a doc's body deliberately
does not, because it cannot change a list of paths.

---

## A passing grade does not mean a useful map

`grader.py` scores this repo's completely empty map at **97.0% PASS** — the same
score it gives the populated map. It measures whether the map is well-*formed*,
not whether it is *useful*, and `generate.py` always emits well-formed output.

Since 2.3.0 the grader prints usefulness **warnings** below the score. They
affect nothing, but they are the part worth reading:

```
  Sections populated             10/19  (diagnostic — not scored)

  ⚠ Vocabulary is empty — the map's primary output produced nothing.
  ⚠ Scanned 47 source file(s) but extracted no routes, models, schemas or features.
```

The first means the map gave you nothing. The second means a parser does not
understand this project's stack. Neither fails the install.

To confirm an extractor actually works, run the tests, not the grader:

```bash
npm test        # 29 assertions across generate / mine-sessions / grader
```

Full detail: [`grading-semantics.md`](../architecture/grading-semantics.md)

## See also

- [`project-map-watch-set.md`](../architecture/project-map-watch-set.md)
- [`skill-parser-contract.md`](../api/skill-parser-contract.md)
