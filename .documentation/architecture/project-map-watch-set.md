---
title: Project map watch set
tier: reference
domains: [architecture]
status: active
last_updated: '2026-09-04'
version: '1.0.0'
purpose: How generate.py decides which files can trigger a regeneration, and why the rules differ per file kind
---

# Project map watch set

`generate.py` regenerates the project map only when its inputs change. What
counts as an input is decided by `collect_watched_files()` and
`collect_doc_files()`, and the rules deliberately differ by file kind. This is
the least obvious mechanism in the codebase and the one most likely to be
"simplified" into a bug.

## The short version

| Kind | Matched by | Hashed with mtime? | Effect of editing one |
|---|---|---|---|
| Source (`.py`, `.ts`, `.go`, `.sh`, …) | extension | yes | full regeneration |
| Manifests (`package.json`, `Makefile`, …) | filename | yes | full regeneration |
| Skill / command manifests | **path glob** | yes | full regeneration |
| Documentation (`.md`, `.rst`, …) | directory + extension | **no** | nothing |

## Why skills match on path, not extension

The obvious fix for "SKILL.md is not watched" is to add `.md` to
`WATCHED_EXTENSIONS`. Don't. That pulls every prose file in the repository into
the watch set, so editing one paragraph of a design doc re-parses the entire
codebase and rewrites all 19 sections.

Instead `WATCHED_GLOBS` matches on the *shape of the path*:

```python
WATCHED_GLOBS = (
    'skills/*/SKILL.md',
    'commands/*.md',
    '.claude/skills/*/SKILL.md',
    '.claude/commands/*.md',
)
```

The match runs `fnmatch` against the **repo-relative posix path**, which is what
anchors each glob at the repository root:

```
commands/status.md                          -> matches
.documentation/reference/commands/cli.md    -> does NOT match
node_modules/foo/commands/x.md              -> does NOT match
```

Matching against the absolute path or the bare filename would let any nested
directory called `commands/` masquerade as a manifest folder. There is a
regression test for exactly this (`test_globs_anchor_at_repo_root`).

`fnmatch` is stdlib. `PurePath.full_match()` reads better but is Python 3.13+,
and the supported floor is 3.8 with 3.12 as the common runtime.

## Why documentation is hashed without mtime

Docs sit in the checksum by **path only**:

```python
for f in doc_files or []:
    h.update(str(f).encode())      # no st_mtime_ns
```

That produces the behaviour section 19 actually needs:

- add, rename or delete a doc → the path set changes → checksum moves → the
  pointer list regenerates
- edit the body of an existing doc → path set identical → checksum unchanged →
  no regeneration

Section 19 lists document *paths*. It never reads document *content*, so a body
edit genuinely cannot change the map. Hashing doc mtimes would force a full
regeneration on every prose commit for no output difference.

## One walk, two consumers

`collect_doc_files()` is the single source of truth. Both the checksum and
`build_doc_pointers_section()` call it, so the set of docs that can *trigger* a
regeneration and the set that gets *listed* cannot drift apart.

They used to be separate walks, and drifted: the checksum knew nothing about
docs at all, while section 19 had its own inline directory list plus a separate
root `*.md` glob. Any future change to what counts as a doc goes in `DOC_DIRS` /
`DOC_EXTS` / `DOC_SKIP_NAMES` / `DOC_SKIP_DIRS`, never in the section builder.

### Skips

`DOC_SKIP_NAMES` drops `INDEX.md` and `REGISTRY.md`; `DOC_SKIP_DIRS` drops
`archive/`. In a hit-em-with-the-docs tree these are generated navigation and
retired content respectively. Without the skips a 15-domain tree contributes 32
nav files, which crowds every real document out of section 19's 30-entry cap —
measured on this repo: 39 doc files in, 6 useful ones out.

## `.claude` is still ignored

`.claude` remains in `IGNORE_DIRS`, so the two `.claude/*` entries in
`WATCHED_GLOBS` are inert. They are kept as the anchor for when that changes.

This is deliberate. Plugin repositories keep `skills/` and `commands/` at the
root, which the root globs already cover. Removing `.claude` from `IGNORE_DIRS`
would expose babel-fish's own engine — `generate.py`, `grader.py`,
`mine-sessions.py` and four shell scripts all live under `.claude/` — to every
extractor, and risks the map indexing its own output.

`SkillParser` and `ToolsScanner` both reach `.claude/skills` through a *direct*
glob, bypassing the watch list. A consuming project's installed skills are
therefore parsed, but changes to them do not by themselves trigger a
regeneration; they are picked up on the next run triggered by something else.

## See also

- [`skill-parser-contract.md`](../api/skill-parser-contract.md) — what the parser reads out of those manifests
- [`map-is-empty.md`](../troubleshooting/map-is-empty.md) — symptoms when this goes wrong
