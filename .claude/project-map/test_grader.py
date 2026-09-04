#!/usr/bin/env python3
"""Regression tests for grader.py — run: python3 .claude/project-map/test_grader.py

Guards the fixes from issue #9. The headline defect there was that the grader
scored a completely empty map and a populated one identically (97.0% both), so
these assert the SIGNAL that separates them, not the score — deliberately, since
folding usefulness into the weighted score would fail legitimately sparse repos.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent


def load_grader(map_dir: Path):
    spec = importlib.util.spec_from_file_location("grader_under_test", HERE / "grader.py")
    g = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["grader.py"]
    try:
        spec.loader.exec_module(g)
    finally:
        sys.argv = argv
    g.MAP_DIR = map_dir
    g.SECTIONS_DIR = map_dir / "sections"
    g.PROJECT_ROOT = map_dir
    return g


def write_map(map_dir: Path, *, vocab: int, scanned: int, extracted: int = 0) -> None:
    (map_dir / "sections").mkdir(parents=True, exist_ok=True)
    (map_dir / "PROJECT_MAP.md").write_text(f"""## Stats

| Metric | Count |
|--------|-------|
| API Routes | {extracted} |
| Data Models | 0 |
| Schemas/DTOs | 0 |
| Frontend Features | 0 |
| Vocabulary Entries | {vocab} |

### Source files scanned

| Language | Files |
|----------|-------|
| python | {scanned} |

## Section Index
""")


def test_empty_vocabulary_warns(tmp):
    write_map(tmp, vocab=0, scanned=0)
    w = load_grader(tmp).usefulness_warnings()
    assert any("Vocabulary is empty" in x for x in w), w


def test_populated_vocabulary_does_not_warn(tmp):
    write_map(tmp, vocab=10, scanned=3)
    w = load_grader(tmp).usefulness_warnings()
    assert not any("Vocabulary is empty" in x for x in w), w


def test_many_files_no_extraction_warns(tmp):
    write_map(tmp, vocab=7, scanned=47, extracted=0)
    w = load_grader(tmp).usefulness_warnings()
    assert any("Scanned 47" in x for x in w), w


def test_few_files_no_extraction_is_quiet(tmp):
    """This repo: 3 CLI shims yielding no routes is correct, not a defect."""
    write_map(tmp, vocab=10, scanned=3, extracted=0)
    w = load_grader(tmp).usefulness_warnings()
    assert not any("Scanned" in x for x in w), w


def test_warnings_do_not_touch_the_score(tmp):
    """Usefulness is reported, never scored — scoring it would fail sparse repos."""
    g = load_grader(tmp)
    write_map(tmp, vocab=0, scanned=99)
    for name in dir(g):
        if name.startswith("grade_"):
            r = getattr(g, name)()
            assert 0.0 <= r.raw_score <= 100.0
    assert g.usefulness_warnings(), "expected warnings for an empty map"


def test_populated_chains_not_misread_as_empty(tmp):
    """`or '_No' in content` matched _Note / _Nothing anywhere in the file and
    scored a populated section as an acceptable empty one at a flat 80%."""
    (tmp / "sections").mkdir(parents=True, exist_ok=True)
    (tmp / "sections" / "12-import-chains.md").write_text(
        "# Section 12\n\n_Note: partial._\n\n```\nsrc/a.py -> src/b.py\n```\n")
    g = load_grader(tmp)
    r = g.grade_import_chains()
    assert "No chains traced" not in r.details, (
        f"a populated section was scored as empty: {r.details}")


def test_stub_chains_still_recognised(tmp):
    (tmp / "sections").mkdir(parents=True, exist_ok=True)
    (tmp / "sections" / "12-import-chains.md").write_text(
        "# Section 12\n\n_No import chains traced._\n")
    r = load_grader(tmp).grade_import_chains()
    assert "No chains traced" in r.details, r.details


def test_empty_vocab_section_reaches_greenfield_branch(tmp):
    """generate.py used to emit a placeholder TABLE ROW, which parsed as a valid
    entry with a neutral location — scoring an empty vocabulary 100% and leaving
    this branch permanently unreachable."""
    (tmp / "sections").mkdir(parents=True, exist_ok=True)
    (tmp / "sections" / "01-vocabulary.md").write_text(
        "# Section 01\n\n| Alias | Type | Location | Notes |\n|---|---|---|---|\n\n"
        "_No vocabulary generated yet — add source code to populate._\n")
    r = load_grader(tmp).grade_vocabulary_accuracy()
    assert r.raw_score == 85.0, f"greenfield branch not reached: {r.raw_score} {r.details}"


def test_generate_emits_prose_not_a_row_for_empty_vocab():
    spec = importlib.util.spec_from_file_location("gen", HERE / "generate.py")
    gen = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["generate.py"]
    try:
        spec.loader.exec_module(gen)
    finally:
        sys.argv = argv
    out = gen.build_vocabulary_section([])
    rows = [l for l in out.splitlines()
            if l.strip().startswith("|") and "Alias" not in l and set(l.strip()) - set("|-: ")]
    assert not rows, f"empty vocabulary must not emit a table row, got {rows}"
    assert "No vocabulary generated yet" in out


def main() -> int:
    import inspect
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = []
    base = Path(tempfile.mkdtemp(prefix="grader-test-"))
    try:
        for fn in tests:
            d = base / fn.__name__
            d.mkdir(parents=True)
            try:
                if "tmp" in inspect.signature(fn).parameters:
                    fn(d)
                else:
                    fn()
                print(f"  ok   {fn.__name__}")
            except Exception as e:
                failed.append(fn.__name__)
                print(f"  FAIL {fn.__name__}: {type(e).__name__}: {e}")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
