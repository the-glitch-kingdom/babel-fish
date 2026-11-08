---
title: Babel-fish glossary contract
tier: reference
domains: [api, architecture]
status: active
last_updated: '2026-11-07'
version: '3.0.1'
purpose: The glossary.json artifact babel-fish emits for machine consumers, and the stability rules around it
---

# Babel-fish glossary contract

babel-fish emits a structured glossary alongside the human-readable project map.
Consumers read that file. **The markdown is not a parsing target.**

## The artifact

`.claude/project-map/glossary.json`, rewritten on every map generation and
staged by the pre-commit hook.

```json
{
  "schema_version": "2.0",
  "generated_at": "2026-11-08T02:26:12Z",
  "source": ".claude/project-map/sections/01-vocabulary.md",
  "project": "babel-fish",
  "entry_count": 7,
  "entries": [
    {
      "key": "policy",
      "aliases": ["policy", "/policy"],
      "canonical_path": "commands/policy.md",
      "paths": ["commands/policy.md"],
      "dirs": [],
      "section": "command",
      "description": "Get or set the babel-fish update policy (auto | nudge | off)",
      "score": null,
      "specificity": 0.2093
    },
    {
      "key": "deal pipeline",
      "aliases": ["deal pipeline"],
      "canonical_path": "src/deals/pipeline.py",
      "paths": ["src/deals/pipeline.py", "src/deals/views.py"],
      "dirs": [],
      "section": "learned",
      "description": "learned from session (score: 8.0)",
      "score": 8.0,
      "specificity": 0.031
    }
  ]
}
```

### Fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Shape version. Currently `"2.0"`. Refuse a major you do not recognise rather than guessing. |
| `generated_at` | string | ISO 8601 UTC, when the map was last generated |
| `source` | string | Repo-relative path of the human-facing section this was derived from |
| `project` | string | Project name from the detected stack |
| `entry_count` | integer | `entries.length`, for a cheap sanity check |
| `entries[].key` | string | The term, normalized: lowercase, trimmed, no leading `/` or `_`, and `-`, `_` and whitespace runs as one space. Unique. |
| `entries[].aliases` | string[] | Every spelling that normalizes to `key`, as written (`/x-y`, `x-y`, `x y`). Match a query against these, not only `key`. |
| `entries[].canonical_path` | string \| null | **One** repo-relative file, the best location (for learned terms, the most used), or `null` when the term has no file (a feature directory only, or none). Never a list. Existed when the glossary was generated. |
| `entries[].paths` | string[] | Every file the term resolves to, best first; `canonical_path` is `paths[0]`. Files only, each existed at generation time. |
| `entries[].dirs` | string[] | Directories the term resolves to (frontend feature folders). Usually empty. |
| `entries[].section` | string | Category: `feature`, `model`, `api`, `skill`, `command`, `learned` |
| `entries[].description` | string \| null | Free text, or null |
| `entries[].score` | number \| null | Learned terms: the session-mining score (frequency x recency). `null` for terms parsed from code. |
| `entries[].specificity` | number \| null | Share (0-1) of the repo's source and doc files containing every word of `key`, counted over files git does not ignore, skipping any over 1 MB. High means generic: filter on it rather than rescanning the repo. `null` when there were no files to measure. |

What is left out by default:

- **Test files.** Models, routes and paths under `tests/`, `__tests__/`, or
  named `test_*`, `*.test.*`, `*.spec.*`, `*_test.*` are not vocabulary.
  `generate.py --include-tests` keeps them.
- **Generic learned words.** A learned single-word term whose `specificity` is
  above 0.20 (`config`, `errors`, `active`) is dropped.
- **Gone locations.** A path that no longer exists is dropped on every run, and
  a learned term with no file left is dropped with it.

Entries are sorted by `key`. Keys are unique.

## Why JSON and not the markdown

`01-vocabulary.md` is a rendered table for humans, and it is a poor parsing
target:

- the `Notes` column mixes descriptions with metadata (`3 components`,
  `table/model: Deal`, `learned from session (score: 7.2)`)
- pipe-escaping leaks into values — this repo's own output contains
  `Get or set the babel-fish update policy (auto \| nudge \| off)`
- layout is a presentation decision, and pinning a contract to it means
  presentation changes become breaking changes

Version 1.0 of this contract specified bullet entries
(`- **key** → \`path\` — desc`) that the generator has never emitted — it has
always written a table. Any consumer built strictly to that spec would have
extracted zero entries. Rather than reconcile the two prose formats, the
producer now hands over structured data and the question disappears.

## Stability

- `schema_version` is `MAJOR.MINOR`. New optional fields bump the minor;
  removing or retyping a field bumps the major.
- The file path is stable for babel-fish 2.x and 3.x.
- `entries[].section` values may gain new members as new extractors are added.
  Treat an unknown section as a valid category, not an error.
- An empty `entries` array is valid and means the map found no vocabulary. It
  is not an error condition — see
  [`grading-semantics.md`](../architecture/grading-semantics.md).

### 2.0: what changed from 1.0

Issue [#38](https://github.com/the-glitch-kingdom/babel-fish/issues/38),
measured on a 1,168-entry FastAPI + React repo: a third of `canonical_path`
values were comma-joined lists (up to 10 paths, directories and deleted files
included), one term appeared under several spellings as several entries, test
models were vocabulary, and generic learned words matched almost every query.

- `canonical_path` changed meaning: one file or `null`, where 1.0 could hold
  `"a.jsx, b.css, src"`. This is the breaking change behind the major bump.
- New: `aliases`, `paths`, `dirs`, `score`, `specificity`.
- Fewer entries: spellings are merged, test files, generic learned words and
  learned terms with no existing file are dropped.

A 1.0 reader that only reads `key` and `canonical_path` still works, but it
sees normalized keys (`policy` instead of a separate `/policy` entry) and
`null` where it got a list.

## Where the output actually lives

| | Path |
|---|---|
| Section files | `.claude/project-map/sections/` |
| Vocabulary (human) | `.claude/project-map/sections/01-vocabulary.md` |
| Glossary (machine) | `.claude/project-map/glossary.json` |

Version 1.0 of this document referred throughout to a `.babel-fish/` directory.
babel-fish has never written to that path — `generate.py` resolves its output
directory from the script's own location, under `.claude/project-map/`. The same
error is mirrored in semantic-memory's `smart-middle-activation.md` and
`corpora-json.md`, so both sides of the contract independently documented a
directory neither produced. Tracked as
[semantic-memory#28](https://github.com/the-glitch-kingdom/semantic-memory/issues/28).

## Consumer notes

Detection: the presence of `.claude/project-map/glossary.json`.

Regeneration is automatic on commit via the pre-commit hook, or manual:

```bash
python3 .claude/project-map/generate.py --force
```

Each project has its own glossary. There is no shared or global vocabulary.

## See also

- [`skill-parser-contract.md`](./skill-parser-contract.md) — how skill manifests become entries
- [`session-vocabulary-mining.md`](../architecture/session-vocabulary-mining.md) — how `learned` entries are produced
- [`integration-with-semantic-memory.md`](../quickstart/integration-with-semantic-memory.md)
