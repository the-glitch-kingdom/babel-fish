---
title: Grading semantics
tier: reference
domains: [architecture]
status: active
last_updated: '2026-09-04'
version: '1.0.0'
purpose: What grader.py measures and what it deliberately does not, and why usefulness is warned about rather than scored
---

# Grading semantics

`grader.py` scores a generated map 0–100 across seven weighted categories and
exits 0 at or above 90%. It is worth being precise about what that number means,
because it is easy to read it as a quality score and it is not one.

## It measures form, not usefulness

| Category | Weight | Question it answers |
|---|---|---|
| Section completeness | 25% | Are all 19 section files present? |
| Vocabulary accuracy | 20% | Do vocabulary entries point at files that exist? |
| Import chain validity | 15% | Do traced chains reference real modules? |
| Secret safety | 15% | Did anything leak? |
| Section size bounds | 10% | Is each section 0.1–50 KB? |
| Structural integrity | 10% | Valid markdown, working TOC links? |
| Checksum functionality | 5% | Does re-running skip correctly? |

Every one is a question about **shape**. None asks whether the map contains
anything worth reading.

`generate.py` always emits well-formed output — correct sizes, valid TOC, real
checksums — even when it has nothing to say. So a map with zero content maxes
out every category. The genuinely empty map this repo produced before
[#6](https://github.com/TheGlitchKing/babel-fish/issues/6) scored **97.0% PASS**,
identical category-for-category to today's populated one.

**A passing grade is not evidence the map is useful.** Use `npm test` to confirm
an extractor works.

## Why usefulness is not scored

The obvious fix — score completeness on populated sections rather than filenames
— was measured and rejected. It fails the *correct* map too:

```
                                      empty map   good map
as shipped                                 97.0       97.0
completeness = populated/19                80.8       85.2   <- both FAIL
```

19 sections is aspirational, not a target. A plugin repo can never populate
routes, models, schemas or migrations, so `populated/19` tops out near 10/19
even when the map is perfect. Scoring it would fail every legitimately sparse
repo — a worse failure than the one it fixes.

More fundamentally: **the difference is not in the map.** An empty map from a
greenfield repo and an empty map from a broken extractor are near-identical
artifacts. Distinguishing them needs to know whether the repo *had* content to
extract, which is knowledge `generate.py` holds and the map did not record.

## The warnings

Reported after the score, affecting nothing:

**Vocabulary is empty.** Vocabulary is what babel-fish is for; zero entries
means the map gave the user nothing regardless of form. This is the signal that
would have surfaced #6 at install time.

**Scanned N source files, extracted nothing.** Fires at 10 or more files with no
routes, models, schemas or features — a parser that does not fit the stack,
rather than a repo with nothing to find. The threshold deliberately keeps small
repos quiet: this one scans 3 CLI shims and correctly extracts no routes.

**Sections populated: N/19.** Coverage context. Not a target, and by itself a
weak discriminator — both the empty and populated maps here report 10/19.

## Two fixed scoring bugs

Neither solved the headline problem; both were real.

The greenfield branch in `grade_vocabulary_accuracy()` was unreachable code.
`build_vocabulary_section()` emitted a placeholder *table row* for an empty
vocabulary, which parsed as a valid entry whose blank location counted as
neutral — scoring 1/1 = 100% and stepping over the `if not rows` branch that
existed to award 85%. It now emits prose.

`or '_No' in content` in `grade_import_chains()` matched that substring
*anywhere*, so a populated section containing `_Note` or `_Nothing` was scored
as an acceptable empty one at a flat 80%. Removed; the exact stub match remains.

## See also

- [`project-map-watch-set.md`](./project-map-watch-set.md)
- [`map-is-empty.md`](../troubleshooting/map-is-empty.md)
