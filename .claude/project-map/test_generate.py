#!/usr/bin/env python3
"""Regression tests for generate.py — run: python3 .claude/project-map/test_generate.py

Stdlib assert + __main__, no pytest, no fixtures (ponytail: the repo has no test
framework and this doesn't justify adding one).

These exist because grader.py cannot catch what they catch: it scored the
completely empty pre-#6 map at 97.0% PASS, identical to the populated map, since
"Vocabulary Accuracy" reads 100% on zero entries. The grader measures
well-formedness; these measure usefulness.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent


def load_generate(project_root: Path):
    """Fresh module instance bound to project_root."""
    spec = importlib.util.spec_from_file_location("gen_under_test", HERE / "generate.py")
    mod = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["generate.py"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = argv
    mod.PROJECT_ROOT = project_root
    return mod


def make_plugin_repo(root: Path) -> None:
    """The repo shape from #6: markdown skills, slash commands, bash, node shim."""
    (root / "skills/demo-skill").mkdir(parents=True)
    (root / "skills/demo-skill/SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: |\n"
        "  Does the demo thing.\n  Second line of the block scalar.\n---\n\n# Demo\n"
    )
    (root / "commands").mkdir()
    (root / "commands/deploy.md").write_text(
        "---\ndescription: Ship it to production\nallowed-tools: Bash(npx:*)\n---\n\nRun the deploy.\n"
    )
    (root / "install.sh").write_text("#!/usr/bin/env bash\necho hi\n")
    (root / "package.json").write_text('{"name":"demo","scripts":{"build":"tsc"}}\n')
    # A docs tree whose paths must NOT be mistaken for command manifests.
    (root / ".documentation/reference/commands").mkdir(parents=True)
    (root / ".documentation/reference/commands/cli.md").write_text("---\ntitle: CLI\n---\n\nprose\n")
    (root / ".documentation/api").mkdir(parents=True)
    (root / ".documentation/api/contract.md").write_text("---\ntitle: Contract\n---\n\nprose\n")
    (root / ".documentation/api/INDEX.md").write_text("---\ntitle: Index\n---\n\nnav\n")
    (root / ".documentation/archive").mkdir(parents=True)
    (root / ".documentation/archive/old.md").write_text("---\ntitle: Old\n---\n\nretired\n")
    (root / "README.md").write_text("# demo\n")


def checksum(g):
    return g.compute_checksum(g.collect_watched_files(), g.collect_doc_files())


def rel(g, paths):
    return {str(p.relative_to(g.PROJECT_ROOT)) for p in paths}


# ── Watch set ────────────────────────────────────────────────────────────────

def test_manifests_are_watched(g):
    watched = rel(g, g.collect_watched_files())
    assert "skills/demo-skill/SKILL.md" in watched, watched
    assert "commands/deploy.md" in watched, watched
    assert "install.sh" in watched, "issue #6: .sh was unwatched, so section 10 never refreshed"


def test_globs_anchor_at_repo_root(g):
    """The whole reason for fnmatch-on-relative-path instead of adding '.md'."""
    watched = rel(g, g.collect_watched_files())
    assert ".documentation/reference/commands/cli.md" not in watched, (
        "a docs tree named commands/ leaked into the watch set — glob is not anchored"
    )
    assert not any(w.startswith(".documentation/") for w in watched), watched


def test_editing_a_skill_moves_the_checksum(g):
    """The #6 blocker: this was bit-identical before the fix."""
    before = checksum(g)
    p = g.PROJECT_ROOT / "skills/demo-skill/SKILL.md"
    p.write_text(p.read_text() + "\nmore\n")
    assert checksum(g) != before, "editing SKILL.md left the checksum unchanged"


# ── Doc pointers ─────────────────────────────────────────────────────────────

def test_adding_a_doc_moves_checksum_editing_one_does_not(g):
    before = checksum(g)
    newdoc = g.PROJECT_ROOT / ".documentation/api/added.md"
    newdoc.write_text("---\ntitle: Added\n---\n\nbody\n")
    after_add = checksum(g)
    assert after_add != before, "adding a doc must refresh section 19"

    newdoc.write_text("---\ntitle: Added\n---\n\nbody, substantially rewritten\n")
    assert checksum(g) == after_add, "editing a doc body must NOT churn the whole map"

    newdoc.unlink()
    assert checksum(g) == before, "deleting a doc must refresh section 19"


def test_doc_pointers_exclude_nav_and_archive(g):
    docs = rel(g, g.collect_doc_files())
    assert ".documentation/api/contract.md" in docs, docs
    assert "README.md" in docs, "section 19's root *.md glob must be covered"
    assert ".documentation/api/INDEX.md" not in docs, "hewtd nav crowds out real docs"
    assert ".documentation/archive/old.md" not in docs, "archived docs are not pointers"


# ── SkillParser ──────────────────────────────────────────────────────────────

def _parsed(g):
    return {m["name"]: m for m in g.SkillParser().parse()}


def test_skill_and_command_parsed(g):
    got = _parsed(g)
    assert "demo-skill" in got, got
    assert "deploy" in got, "commands/*.md carry no 'name:' — it comes from the filename"
    assert got["demo-skill"]["kind"] == "skill"
    assert got["deploy"]["kind"] == "command"
    assert "Second line" in got["demo-skill"]["description"], "block scalar not joined"
    assert got["deploy"]["description"] == "Ship it to production"


def test_regex_fallback_matches_yaml(g):
    """babel-fish only suggests pyyaml, so the fallback is the common path."""
    if not g.HAS_YAML:
        return  # nothing to compare against
    with_yaml = _parsed(g)
    g.HAS_YAML = False
    try:
        without = _parsed(g)
    finally:
        g.HAS_YAML = True
    assert set(with_yaml) == set(without), (set(with_yaml), set(without))
    for k in with_yaml:
        assert with_yaml[k]["description"] == without[k]["description"], k


# ── End to end ───────────────────────────────────────────────────────────────

def test_plugin_repo_map_is_not_empty(g):
    """The test that fails if #6 regresses."""
    skills = g.SkillParser().parse()
    vocab = g.VocabularyBuilder().build([], [], [], [], g.load_stack(), skills)
    aliases = {v["alias"] for v in vocab}
    assert aliases, "a plugin repo produced an empty vocabulary — issue #6"
    assert "demo skill" in aliases or "demo-skill" in aliases, aliases
    assert "/deploy" in aliases, "commands should be reachable as /name"
    assert "deploy" in aliases, "...and as a bare word"

    tools = {t["name"] for t in g.ToolsScanner().scan()}
    assert "/deploy" in tools, tools

    section = g.build_vocabulary_section(vocab)
    assert "no vocabulary generated yet" not in section, "section 01 still renders the stub"


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = []
    tmp = Path(tempfile.mkdtemp(prefix="babelfish-test-"))
    try:
        for fn in tests:
            root = tmp / fn.__name__
            root.mkdir()
            make_plugin_repo(root)
            g = load_generate(root)
            try:
                fn(g)
                print(f"  ok   {fn.__name__}")
            except Exception as e:
                # Exception, not just AssertionError: against an older
                # generate.py the new helpers are simply absent, and that
                # should read as a failing test, not abort the whole run.
                failed.append((fn.__name__, e))
                print(f"  FAIL {fn.__name__}: {type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
