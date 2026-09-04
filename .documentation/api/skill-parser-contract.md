---
title: Skill parser contract
tier: reference
domains: [api, architecture]
status: active
last_updated: '2026-09-04'
version: '1.0.0'
purpose: Which frontmatter fields SkillParser reads from skill and command manifests, and how they become vocabulary entries
---

# Skill parser contract

In a plugin or skill repository there are no routes, models or schemas to
extract — but a skill's frontmatter is already an alias-to-location pair, which
is precisely what section 01 wants. `SkillParser` turns manifests into
vocabulary and tool entries without adding any new map sections.

## What it reads

| Pattern | Kind |
|---|---|
| `skills/*/SKILL.md` | skill |
| `.claude/skills/*/SKILL.md` | skill |
| `commands/*.md` | command |
| `.claude/commands/*.md` | command |

Only two frontmatter fields are consumed:

| Field | Required | Fallback |
|---|---|---|
| `name` | no | directory name for `SKILL.md`, filename stem for a command |
| `description` | no | empty; the entry still appears |

`name` is optional because the two manifest kinds are shaped differently. A
skill declares it:

```yaml
---
name: babel-fish-developer-skill
description: |
  Full-stack developer context for any project with Babel Fish installed.
  Provides instant access to project map and vocabulary translation.
---
```

A slash command does not — its identity is the filename:

```yaml
---
description: Get or set the babel-fish update policy (auto | nudge | off)
allowed-tools: Bash(npx:*)
---
```

So `commands/policy.md` becomes `policy`. Every other frontmatter key
(`allowed-tools`, `argument-hint`, …) is ignored.

## Parsing without pyyaml

babel-fish only *suggests* `pyyaml`, so the fallback path is the common case,
not a corner case. `SkillParser._frontmatter()` prefers `yaml.safe_load()` and
falls back to `_frontmatter_regex()`, which handles `key: value` and block
scalars (`|`, `>`, `|-`, `>-`) — enough for the two fields above.

Multi-line block scalars are joined into a single whitespace-normalized line, so
a description written across four lines becomes one. Both readers are asserted
to agree on `name` and `description` in `test_regex_fallback_matches_yaml`.

If a manifest has no leading `---` block, it is skipped silently — a `SKILL.md`
that is pure prose is not an error.

## What it produces

Each manifest yields `{name, kind, file, description}`, consumed twice:

**Vocabulary (section 01)** — via `VocabularyBuilder.build(..., skills)`. The
name is expanded through `_name_to_aliases()`, so `demo-skill` also resolves as
`demo skill`. Commands additionally get a `/name` alias, because humans say both
"status" and "/status".

**Tools (section 10)** — via `ToolsScanner.scan()`, deduped against the
existing `.claude/skills` walk so a skill present in both places is listed once.

Deduplication is by file path, and the patterns are ordered so a root `skills/`
manifest wins over the same skill installed under `.claude/skills/`.

## How entries reach a consumer

Vocabulary is emitted twice: as a markdown table in `01-vocabulary.md` for
humans, and as structured records in
[`glossary.json`](./glossary-contract.md) for machines. Skill and command
entries appear in both, with `section` set to `skill` or `command`.

Consumers read the JSON. The markdown is not a parsing target — see the contract
for why.

## See also

- [`project-map-watch-set.md`](../architecture/project-map-watch-set.md) — when these manifests trigger a regeneration
- [`glossary-contract.md`](./glossary-contract.md) — the downstream semantic-memory contract
