---
title: Session vocabulary mining
tier: reference
domains: [architecture]
status: active
last_updated: '2026-09-04'
version: '1.0.0'
purpose: How mine-sessions.py turns Claude Code transcripts into learned aliases, and the transcript-shape assumptions it depends on
---

# Session vocabulary mining

`mine-sessions.py` reads Claude Code transcripts and learns that when you say
"the deals page", the file you meant was `src/features/deals/DealPipeline.tsx`.
Those aliases feed section 01 (vocabulary) and section 17 (learned vocabulary).

It is the only part of babel-fish that reads data from outside the repository,
which makes it the part most exposed to a format it does not control.

## Pipeline

```
~/.claude/projects/<slug>/*.jsonl
  → find_session_files()      pick this project's transcripts
  → parse_session()           JSONL → messages
  → is_user_turn()            keep genuine human turns
  → extract_user_phrases()    prose → candidate aliases
  → pair with file activity   within the same assistant turn
  → score frequency × recency
  → learned-vocabulary.json   consumed by generate.py
```

## Transcript shape assumptions

These are the load-bearing facts about the JSONL. Each one, when wrong, makes
the miner silently produce nothing — it never raises.

**Content is nested.** Role and content live at `msg["message"]["role"]` and
`msg["message"]["content"]`, not at the top level. `msg_content()` and
`msg_role()` are the only places that know this; they prefer the nested shape
and fall back to flat for older or third-party transcripts. Reading the top
level yielded 0 tool_use blocks where the nested read found 157.

**Tool results wear the user's role.** A tool result is delivered as
`role: "user"` with a `tool_result` content block. In one real transcript, 167
of 181 `role=user` messages were tool results. `is_user_turn()` therefore
requires an actual `text` block — without that, the pairing window closes on the
assistant's own output.

**Injected text also wears the user's role.** Skill bodies and slash-command
definitions arrive in the user slot carrying `isMeta: true`, and they are large
(255 KB against 40–290 characters for a real message). Mining them taught the
miner aliases from the injected documents themselves — `block_index_edits`,
`superseded by v2 guide`, and `refactor authentication system`, the last lifted
from a skill's own worked example. `isMeta` and `isSidechain` are skipped.

**Directory slugs keep the leading separator.** `/home/u/proj` maps to
`-home-u-proj`. Stripping it means the exact match never hits and every lookup
falls through to a fuzzy substring match — which is unsafe as anything but a
last resort, because a name like `kentro` matches four unrelated project
directories whose aliases would be attributed here.

## Pairing and scoring

For each genuine user turn, every file the assistant touched before the next
genuine user turn is a candidate target, bounded by `MAX_LOOKAHEAD`. Each
(phrase, path) pair scores `frequency × recency_weight` — 1.0 within 30 days,
0.5 to 60, 0.25 to 90, dropped beyond. `MIN_SCORE = 5.0` filters one-offs, so an
alias must be used repeatedly to be learned.

### File activity includes Bash

`FILE_TOOL_NAMES` covers Read/Edit/Write/Grep/Glob, but a real session ran 148
Bash calls against 2 Read and 2 Edit. Paths are therefore also taken from Bash
command strings — but only tokens that resolve to a file that actually exists in
the repo. A confidently wrong alias is worse than a missing one, so there is
deliberately no smarter shell parsing than that.

## The cursor is a correctness requirement

`.mine-cursor.json` records the newest transcript mtime mined. This is not only
about cost: `merge_learned()` **adds** scores, so re-mining a counted transcript
inflates it without bound. Running at every session start without the cursor
would corrupt the scores the feature exists to produce. `--all` forces a full
re-mine.

## Timing

The SessionStart hook sees transcripts through the *previous* session — the
current one is not written yet — so an alias lands one session after it is first
used. A SessionEnd hook would be exact, at the cost of a second hook for one
session of latency.

## Expect little from an operational session

The miner learns feature nouns: "the deals page", "the billing workflow". A
session spent on refactoring, tooling or release work contains few such phrases
and will correctly mine nothing. An empty result is not by itself a fault — see
[learned vocabulary is empty](../troubleshooting/learned-vocabulary-empty.md).

## See also

- [`project-map-watch-set.md`](./project-map-watch-set.md)
- [`skill-parser-contract.md`](../api/skill-parser-contract.md)
