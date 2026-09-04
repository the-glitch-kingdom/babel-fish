---
title: Learned vocabulary is empty
tier: guide
domains: [troubleshooting]
status: active
last_updated: '2026-09-04'
version: '1.0.0'
purpose: Why section 17 has no entries, and how to tell an expected empty result from a broken miner
---

# Learned vocabulary is empty

`17-learned-vocabulary.md` says "No session-mined vocabulary yet" and
`learned-vocabulary.json` is `{}`.

The miner never raises on failure. It exits 0 and reports
`Extracted 0 alias(es)`, which looks identical whether it is working correctly
or completely broken. Work down in order.

## 1. Is it expected?

The miner learns **feature nouns** — "the deals page", "the billing workflow".
A session spent on refactoring, tooling, releases or infrastructure contains few
such phrases, and mining it correctly yields nothing.

Reality check: run it against a product repo with months of history.

```bash
python3 .claude/project-map/mine-sessions.py --dry-run --verbose --all \
  --project-root /path/to/a/product/repo
```

Non-zero there and zero here is not a bug — it is the feature working.

## 2. Are there transcripts to mine?

```bash
python3 .claude/project-map/mine-sessions.py --dry-run --verbose --all
```

`No session files found` means discovery failed. Directory names under
`~/.claude/projects/` keep the leading separator (`-home-u-proj`); confirm one
exists for this repo's absolute path. A project moved to a new path has its
history under the old slug.

## 3. Has the cursor already consumed them?

`No transcripts changed since last run` means the cursor is doing its job. It
exists because `merge_learned()` adds scores, so re-mining would inflate them.
To re-examine everything without writing:

```bash
python3 .claude/project-map/mine-sessions.py --dry-run --verbose --all
```

Delete `.claude/project-map/.mine-cursor.json` to genuinely re-mine from
scratch — and reset `learned-vocabulary.json` at the same time, or the scores
double.

## 4. Did it mine, but score below threshold?

`MIN_SCORE = 5.0` needs an alias used roughly five times inside 30 days. A
phrase said once is deliberately dropped. `--verbose` prints what was found
before the cut.

## 5. Is the transcript format still what the miner expects?

The most likely cause of a *silent* zero on a repo that should produce results.
The miner depends on facts about a format it does not own — nested
`message.content`, `role: "user"` on tool results, `isMeta` on injected text.
If Claude Code changes any of them, the miner keeps exiting 0 and learning
nothing.

Quick probe:

```bash
python3 - <<'PY'
import json, pathlib
d = sorted((pathlib.Path.home()/'.claude'/'projects').glob('*/*.jsonl'))[-1]
rows = [json.loads(l) for l in open(d, encoding='utf-8', errors='replace') if l.strip()]
nested = sum(1 for r in rows if isinstance(r.get('message'), dict))
tools  = sum(1 for r in rows if isinstance(r.get('message'), dict)
             for b in (r['message'].get('content') or [])
             if isinstance(b, dict) and b.get('type') == 'tool_use')
print(f"{d.name}: {len(rows)} rows, {nested} nested, {tools} tool_use")
PY
```

`nested` at 0 means the shape moved and `msg_content()` needs updating. Then run
`python3 .claude/project-map/test_mine_sessions.py` — its fixtures encode the
expected shape, so a real format change should break them.

## See also

- [`session-vocabulary-mining.md`](../architecture/session-vocabulary-mining.md)
- [`map-is-empty.md`](./map-is-empty.md)
