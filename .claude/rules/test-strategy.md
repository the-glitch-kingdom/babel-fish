# babel-fish — Test Strategy

> Written once by babel-fish; yours to edit.

The most confidence for the least compute: each behavior is tested once, at the cheapest level that proves it.

1. **Test what callers and users depend on, once**: one test per behavior, plus its edge cases,
   failure paths and each fixed bug. NEVER test the language or framework, private helpers, or the
   same path twice, and never mock the code under test.
2. **Test at the lowest level that proves it.** Most tests are fast unit tests; integration tests
   cover the seams between real parts (database, API, queue); a few end-to-end tests cover the
   critical user journeys. NEVER re-prove at a higher level what a lower one already proves.
3. **Consolidate before adding**: extend an existing test, or add a case to a parametrized one,
   instead of copying a test per case. Share expensive setup (database, server, build) once per run,
   not once per test.
4. **Fast and deterministic**: wait on a condition, never `sleep`; fake the network and the clock
   where a fake proves the same thing; keep tests independent so they run in parallel. A flaky test
   is fixed or deleted, never retried until green. Know the slowest tests, and speed them up or move
   them down a level.
5. **A test worth keeping lives in the test folder** (`tests/`, or where `.claude/structure.toml`
   puts tests), is named for what it covers, and runs in the suite. Never in `src/`, the repo root
   or a scratch folder.
6. **Delete tests that no longer test anything**: tests of removed code, duplicates, skipped tests
   nobody will fix, unused fixtures. A failing test is fixed, never skipped to go green; delete it
   only when the behavior it covers is gone.
