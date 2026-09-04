---
title: Integration with semantic-memory
tier: guide
domains: [quickstart, troubleshooting]
status: active
last_updated: '2026-09-04'
version: '2.0.0'
purpose: What babel-fish provides for semantic-memory to consume, and the current state of that integration
---

# Integration with semantic-memory

> **Status: producer-side only.** babel-fish emits everything the integration
> needs. semantic-memory has not built the consumer yet — as of 1.5.1 it ships
> no `translate` / `reverse_translate` / `list_vocabulary` verbs, no
> `project-map` corpus, and no glossary reader. Its `compat-matrix.md` schedules
> that work for Phase 3.1.0.
>
> Nothing below requires setup today. It documents the artifact so the consumer
> can be built against something real.

## What babel-fish produces

| Artifact | Path | Audience |
|---|---|---|
| Project map sections | `.claude/project-map/sections/` | humans and semantic search |
| Vocabulary (rendered) | `.claude/project-map/sections/01-vocabulary.md` | humans |
| Glossary (structured) | `.claude/project-map/glossary.json` | machines |

Both are regenerated on every map build and staged by the pre-commit hook.

```
┌──────────────┐   pre-commit    ┌────────────────────────────────┐
│  babel-fish  │ ──────────────► │ .claude/project-map/           │
│  (producer)  │   regenerates   │   sections/01-vocabulary.md    │ ← human
└──────────────┘                 │   sections/02..19.md           │
                                 │   glossary.json                │ ← machine
                                 └────────────────────────────────┘
```

## What a consumer should read

`glossary.json`, not the markdown. Full field reference and stability rules:
[`glossary-contract.md`](../api/glossary-contract.md).

```json
{
  "schema_version": "1.0",
  "entry_count": 10,
  "entries": [
    { "key": "/status", "canonical_path": "commands/status.md",
      "section": "command", "description": "Show installed version…" }
  ]
}
```

The markdown table is a rendering. Its `Notes` column mixes descriptions with
metadata and carries pipe-escaping, so parsing it is strictly worse than reading
the JSON that produced it.

## Corpus configuration, when it exists

For indexing the map as prose, the corpus root is the **sections** directory:

```jsonc
{
  "name": "project-map",
  "root": "./.claude/project-map/sections",
  "glob": "**/*.md",
  "chunker": "markdown",
  "enabled": true
}
```

Detection trigger: the presence of `.claude/project-map/glossary.json`.

> Earlier revisions of this document, and semantic-memory's own
> `smart-middle-activation.md` and `corpora-json.md`, specify `.babel-fish/`.
> babel-fish has never written to that path. Tracked as
> [semantic-memory#28](https://github.com/the-glitch-kingdom/semantic-memory/issues/28);
> a consumer built to those docs finds nothing, silently.

## Regeneration

The pre-commit hook rebuilds the map when source files change. Manually:

```bash
python3 .claude/project-map/generate.py --force
```

Each project has its own glossary. There is no shared vocabulary across
projects.

## Troubleshooting

**"glossary.json does not exist"** — the map has never been generated. Run the
command above. If it still does not appear, babel-fish is older than 2.4.0.

**"glossary.json exists but `entries` is empty"** — the map found no
vocabulary. Expected on a repo with no source code; otherwise see
[learned vocabulary is empty](../troubleshooting/learned-vocabulary-empty.md)
and [map is empty](../troubleshooting/map-is-empty.md). An empty array is valid,
not an error.

**"the translate verbs are not registered"** — they do not exist yet. See the
status note at the top.

## See also

- [`glossary-contract.md`](../api/glossary-contract.md) — the artifact specification
- [`skill-parser-contract.md`](../api/skill-parser-contract.md) — where skill and command entries come from
