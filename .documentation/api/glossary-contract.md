---
title: Babel-fish glossary contract
tier: reference
domains: [api, architecture]
status: active
last_updated: '2026-09-04'
version: '2.0.0'
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
  "schema_version": "1.0",
  "generated_at": "2026-09-04T20:03:33Z",
  "source": ".claude/project-map/sections/01-vocabulary.md",
  "project": "babel-fish",
  "entry_count": 10,
  "entries": [
    {
      "key": "/policy",
      "canonical_path": "commands/policy.md",
      "section": "command",
      "description": "Get or set the babel-fish update policy (auto | nudge | off)"
    },
    {
      "key": "/relink",
      "canonical_path": "commands/relink.md",
      "section": "command",
      "description": "Re-run the skill linker — refresh symlinks from node_modules into .claude/skills/"
    }
  ]
}
```

### Fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Shape version. Currently `"1.0"`. Refuse a major you do not recognise rather than guessing. |
| `generated_at` | string | ISO 8601 UTC, when the map was last generated |
| `source` | string | Repo-relative path of the human-facing section this was derived from |
| `project` | string | Project name from the detected stack |
| `entry_count` | integer | `entries.length`, for a cheap sanity check |
| `entries[].key` | string | The human term, e.g. `"deals page"` |
| `entries[].canonical_path` | string | Repo-relative path the term resolves to |
| `entries[].section` | string | Category: `feature`, `model`, `api`, `skill`, `command`, `learned` |
| `entries[].description` | string \| null | Free text, or null |

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
- The file path is stable for babel-fish 2.x.
- `entries[].section` values may gain new members as new extractors are added.
  Treat an unknown section as a valid category, not an error.
- An empty `entries` array is valid and means the map found no vocabulary. It
  is not an error condition — see
  [`grading-semantics.md`](../architecture/grading-semantics.md).

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
