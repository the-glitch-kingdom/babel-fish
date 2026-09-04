---
title: Babel-fish glossary contract
tier: reference
domains: [api, architecture]
status: active
last_updated: '2026-05-07'
version: '1.0.0'
purpose: Producer/consumer data contract for the 01-vocabulary.md glossary side-channel consumed by semantic-memory
---

# Babel-fish glossary contract

This document specifies the structured contract between babel-fish (the producer) and semantic-memory (the consumer) for the vocabulary translation feature.

## Overview

babel-fish auto-generates a 19-section project map under `.babel-fish/`. Section 01 (`01-vocabulary.md`) is the **vocabulary translation layer** — a structured key→value mapping from human terms to canonical code paths. The other 18 sections are general project-map content (routes, models, schemas, infra, etc.).

semantic-memory consumes the project-map directory as a **`project-map` corpus** and additionally extracts `01-vocabulary.md` into a structured `glossary.json` side-channel that powers explicit translation verbs (`translate`, `reverse_translate`, `list_vocabulary`).

This doc defines the contract for that side-channel — the shape, format, and stability rules of `01-vocabulary.md` so semantic-memory can extract it deterministically.

## `01-vocabulary.md` format

The file is a markdown document with a structured "Vocabulary Translation" section. Section content follows this schema:

```markdown
# 01: Vocabulary Translation

> Plain-English → exact file-path mapping. Keep this file authoritative.

## <Section Name>

- **<human term>** → `<canonical-path>` — <optional description>
- **<human term>** → `<canonical-path>` — <optional description>

## <Another Section Name>

- **<human term>** → `<canonical-path>` — <optional description>
```

### Parsing rules

semantic-memory's glossary extractor (`babel-fish-vocabulary` chunker extras) parses the file using these rules:

1. **Section headers** (`## <name>`) become category tags applied to all entries until the next `## ` header
2. **Bullet entries** matching `- **<key>** → \`<path>\` — <description>` are extracted as glossary entries
3. **Bullet entries** matching `- **<key>** → \`<path>\`` (without description) are also valid
4. **Plain bullet entries** (without the bold-arrow-backtick pattern) are ignored — keep prose as prose
5. The `→` (Unicode RIGHTWARDS ARROW, U+2192) is the canonical separator. ASCII `->` also accepted as a fallback.

### Output `glossary.json`

semantic-memory writes the extracted glossary to `.semantic/project-map/glossary.json`:

```json
{
  "schema_version": "1.0",
  "extracted_at": "2026-05-07T12:34:56Z",
  "source": ".babel-fish/01-vocabulary.md",
  "entries": [
    {
      "key": "deals page",
      "canonical_path": "features/deal-pipeline/DealPipeline.tsx",
      "section": "UI Pages",
      "description": "main deal-management view with pipeline columns and metrics"
    },
    {
      "key": "invoice job",
      "canonical_path": "src/jobs/invoice-processor.ts",
      "section": "Background Jobs",
      "description": "nightly invoice generation worker"
    }
  ]
}
```

### Field reference

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Glossary.json schema version. Currently `"1.0"`. Bumps when the extractor's output shape changes. |
| `extracted_at` | string (ISO 8601) | When the extractor last ran |
| `source` | string | Path to the source `01-vocabulary.md` |
| `entries[].key` | string | Human term (e.g., "deals page") |
| `entries[].canonical_path` | string | Code path the term maps to (e.g., `features/deal-pipeline/DealPipeline.tsx`) |
| `entries[].section` | string | Section header from the source file (category tag) |
| `entries[].description` | string \| undefined | Optional description from the source bullet |

### Stability rules

The contract above is **stable for the duration of major version 2.x of babel-fish**. semantic-memory pins `babel-fish ^2.0.0` and trusts that:

- The `## Section Name` → `- **key** → \`path\` — desc` pattern is preserved across babel-fish 2.x minors
- New sections may be added; existing sections may be renamed (with appropriate semver consideration)
- The Unicode arrow character (`→`) is the canonical separator

If babel-fish 3.0 changes the format (e.g., to JSON-Frontmatter-only or a wholly different markdown structure), the glossary extractor in semantic-memory must be updated in lockstep, and dev-stack's matrix bumps to require the matching pair.

## Consumer-side: semantic-memory translation verbs

When semantic-memory's `project-map` corpus is active AND `glossary.json` is present (extracted from babel-fish output), three MCP verbs are registered:

### `translate(human_term, fuzzy?)`

```typescript
translate("deals page")
// → { canonical_path: "features/deal-pipeline/DealPipeline.tsx",
//     section: "UI Pages",
//     confidence: 1.0,
//     description: "main deal-management view ..." }

translate("dealsz page", { fuzzy: true })  // typo
// → { canonical_path: "features/deal-pipeline/DealPipeline.tsx",
//     section: "UI Pages",
//     confidence: 0.85,  // fuzzy match
//     description: "..." }
```

Default is exact match. Pass `fuzzy: true` for tolerant matching (Levenshtein distance ≤ 2 by default).

### `reverse_translate(file_path)`

```typescript
reverse_translate("features/deal-pipeline/DealPipeline.tsx")
// → [{ key: "deals page", section: "UI Pages", description: "..." }]
```

Returns ALL human terms that map to a given path (a path can have multiple aliases).

### `list_vocabulary(section_filter?)`

```typescript
list_vocabulary()
// → all entries across all sections

list_vocabulary("UI Pages")
// → only entries from the UI Pages section
```

## Optional: query-rewriting integration

semantic-memory has an opt-in flag in `corpora.json` for the `project-map` corpus:

```jsonc
{
  "name": "project-map",
  "root": "./.babel-fish",
  "glob": "**/*.md",
  "chunker": "markdown",
  "enabled": true,
  "extras": {
    "glossary_extractor": "babel-fish-vocabulary",
    "vocabulary_query_rewrite": true
  }
}
```

When `vocabulary_query_rewrite: true`, semantic-memory preprocesses search queries: detected human terms are translated to their canonical paths before embedding. So `search_code("how does the deals page work?")` becomes `search_code("how does features/deal-pipeline/DealPipeline.tsx work?")` internally — making the embedding match more deterministic.

This is **off by default** because silent rewriting can confuse users debugging searches. Document the trade-off explicitly when enabling.

## How to author your `01-vocabulary.md`

For maximum signal, author entries in this format consistently:

```markdown
## UI Pages

- **deals page** → `features/deal-pipeline/DealPipeline.tsx` — main deal-management view with pipeline columns and metrics
- **investor portal** → `features/investor-portal/InvestorPortal.tsx` — investor-facing dashboard
- **admin settings** → `features/admin/SettingsPanel.tsx` — admin configuration UI

## Background Jobs

- **invoice job** → `src/jobs/invoice-processor.ts` — nightly invoice generation worker
- **email digest** → `src/jobs/email-digest.ts` — weekly summary mailer

## Models

- **Deal** → `src/models/Deal.ts` — primary deal entity
- **Investor** → `src/models/Investor.ts` — investor account
```

### Tips

- **One entry per logical concept**: don't duplicate. If "deals page" and "deal management view" both map to the same file, list the file once with both keys (separate bullets).
- **Use the description**: the `— description` after the path gives semantic-memory context for fuzzy matching and for `list_vocabulary` UX.
- **Group by purpose**: section headers become category tags. A query against `list_vocabulary("UI Pages")` should return what users would consider UI pages.
- **Path syntax**: use the path format your codebase actually uses. If your IDE uses `features/foo/Foo.tsx`, use that. If it uses `src/features/foo/Foo.tsx`, use that. Consistency matters more than absolute correctness — semantic-memory just stores what you give it.

## Auto-regeneration

babel-fish regenerates the project map on pre-commit. semantic-memory has a file-watcher that detects `01-vocabulary.md` changes and re-extracts `glossary.json` automatically. There's no manual step.

If the file-watcher is disabled (e.g. `--no-watch`), trigger re-extraction manually:

```bash
semantic-memory --notes . --reindex
```

## Inter-PR coordination

This contract was specified as part of the unified memory-layer plan:

- babel-fish 2.0 (already shipped) — produces the 19-section project map including `01-vocabulary.md`
- semantic-memory Phase 3.1.0 (planned) — adds the `project-map` corpus type, glossary extractor, and the three translation verbs
- dev-stack 1.0 (planned) — pins both at compatible versions

This doc lives in babel-fish (the producer) so the contract is owned by the producer side. semantic-memory's `with-babel-fish` cookbook (planned for Phase 4.8.0) will cross-reference this doc as the canonical contract.

## See also

- `~/workspace/the-glitch-kingdom/semantic-sidekick/docs/corpora-json.md` — how the `project-map` corpus is configured
- `~/workspace/the-glitch-kingdom/semantic-sidekick/docs/smart-middle-activation.md` — how semantic-memory auto-detects babel-fish output
- `~/workspace/the-glitch-kingdom/semantic-sidekick/docs/compat-matrix.md` — version pins for babel-fish ↔ semantic-memory
- `~/workspace/the-glitch-kingdom/persistent-planning/.planning/layered-planning-with-mcp-and-hewtd-frontmatter/task_plan.md` — meta-plan; Phase 3.1.0 details
