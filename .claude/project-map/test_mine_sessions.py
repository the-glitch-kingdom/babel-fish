#!/usr/bin/env python3
"""Regression tests for mine-sessions.py — run: python3 .claude/project-map/test_mine_sessions.py

Same shape as test_generate.py: stdlib assert + __main__, no framework.

Every test here corresponds to a defect that shipped and produced NO error —
the miner exited 0 and reported "Extracted 0 alias(es)" for its entire
existence. Silent-zero is the failure mode these guard against.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent


def load_miner(project_root: Path, cursor_dir: Path):
    spec = importlib.util.spec_from_file_location("miner_under_test", HERE / "mine-sessions.py")
    mod = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["mine-sessions.py"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = argv
    mod.PROJECT_ROOT = project_root
    mod.MINE_CURSOR = cursor_dir / ".mine-cursor.json"
    return mod


def write_transcript(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")


def user_msg(text: str, **extra) -> dict:
    """A genuine user turn, in the real nested shape Claude Code writes."""
    return {"type": "user", "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}, **extra}


def tool_msg(name: str, inp: dict) -> dict:
    return {"type": "assistant", "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": {"role": "assistant",
                        "content": [{"type": "tool_use", "name": name, "input": inp}]}}


def tool_result() -> dict:
    """Tool results come back with role=user — the collision that broke pairing."""
    return {"type": "user", "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": {"role": "user",
                        "content": [{"type": "tool_result", "content": "ok"}]}}


# ── Defect 1: JSONL nesting ──────────────────────────────────────────────────

def test_reads_nested_message_content(m, root):
    msg = user_msg("open the settings page")
    assert m.msg_role(msg) == "user", "role must be read from message.role"
    content = m.msg_content(msg)
    assert isinstance(content, list) and content[0]["text"] == "open the settings page"


def test_still_reads_flat_content(m, root):
    """Older/third-party transcripts must not regress."""
    flat = {"role": "user", "content": [{"type": "text", "text": "hello there"}]}
    assert m.msg_role(flat) == "user"
    assert m.msg_content(flat)[0]["text"] == "hello there"


def test_extracts_tool_paths_from_nested(m, root):
    paths = m.extract_file_paths_from_tool_calls(
        [tool_msg("Read", {"file_path": str(root / "src/app.py")})])
    assert paths == ["src/app.py"], paths


# ── Defect 2: regex quantifiers ──────────────────────────────────────────────

def test_the_x_page_pattern_matches(m, root):
    """'{2,40?}' compiled fine and matched nothing — no error, just silence."""
    got = m.extract_user_phrases("please look at the settings page")
    assert "settings" in got, got


def test_x_feature_pattern_matches(m, root):
    got = m.extract_user_phrases("the billing workflow is broken")
    assert any("billing" in g for g in got), got


# ── Defect 3: tool_result / user-turn collision ──────────────────────────────

def test_tool_result_is_not_a_user_turn(m, root):
    assert m.is_user_turn(user_msg("the deals page")) is True
    assert m.is_user_turn(tool_result()) is False, (
        "tool results carry role=user; treating them as user turns closed the "
        "pairing window on the assistant's own output"
    )


def test_meta_and_sidechain_are_not_user_turns(m, root):
    assert m.is_user_turn(user_msg("skill body text", isMeta=True)) is False
    assert m.is_user_turn(user_msg("subagent text", isSidechain=True)) is False


# ── Defect 4: Bash-mediated file access ──────────────────────────────────────

def test_bash_paths_extracted_when_file_exists(m, root):
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src/app.py").write_text("# app\n")
    got = m.extract_paths_from_bash("sed -n '1,40p' src/app.py", root)
    assert got == ["src/app.py"], got


def test_bash_paths_ignore_nonexistent(m, root):
    got = m.extract_paths_from_bash("cat totally/made/up.py && ls -la", root)
    assert got == [], f"only real files may become aliases, got {got}"


# ── Defect 6: session discovery ──────────────────────────────────────────────

def test_slug_keeps_leading_separator(m, root, monkey_home):
    """.lstrip('-') meant the exact match never hit, so every lookup fell
    through to a fuzzy substring match that ALSO ran additively. A decoy
    sharing the project name proves the exact path is used and that another
    project's transcripts are not swept in — "kentro" matches four real
    directories on this machine."""
    projects = monkey_home / ".claude" / "projects"
    slug = str(root).replace("/", "-")
    (projects / slug).mkdir(parents=True)
    write_transcript(projects / slug / "s.jsonl", [user_msg("hi there")])

    decoy = projects / (slug + "-other-project")
    decoy.mkdir(parents=True)
    write_transcript(decoy / "d.jsonl", [user_msg("decoy transcript")])

    found = m.find_session_files(root)
    assert len(found) == 1, f"expected only the exact match, got {found}"
    assert found[0].parent.name == slug, found[0]


# ── End to end ───────────────────────────────────────────────────────────────

def test_mines_alias_to_path(m, root, monkey_home):
    """The test that fails if any defect returns."""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src/deals.py").write_text("# deals\n")
    slug = str(root).replace("/", "-")
    d = monkey_home / ".claude" / "projects" / slug
    d.mkdir(parents=True)

    entries = []
    for _ in range(6):  # clear MIN_SCORE = 5.0 at weight 1.0
        entries.append(user_msg("update the deals page please"))
        entries.append(tool_msg("Read", {"file_path": str(root / "src/deals.py")}))
        entries.append(tool_result())
    write_transcript(d / "s.jsonl", entries)

    miner = m.SessionMiner(root)
    miner.mine(m.find_session_files(root))
    res = miner.results()
    assert res, "mined nothing from a transcript containing 6 clear pairings"
    assert "deals" in res, list(res)
    assert "src/deals.py" in res["deals"]["targets"], res["deals"]


def test_junk_phrases_filtered(m, root):
    got = m.extract_user_phrases('he said "that, if not" and "total documents:"')
    assert not any("," in g or ":" in g for g in got), got


def test_project_root_relocates_miner_output(m, root):
    """Mining another project used to write its aliases into THIS project's
    learned vocabulary."""
    target = root / "elsewhere"
    target.mkdir(parents=True)
    m.configure_paths(target)
    assert m.PROJECT_ROOT == target
    for name in ("LEARNED_VOC", "MINE_CURSOR"):
        p = getattr(m, name)
        assert str(p).startswith(str(target)), f"{name} outside target: {p}"
    assert m.LEARNED_VOC.parent.is_dir()


def main() -> int:
    import inspect
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = []
    tmp = Path(tempfile.mkdtemp(prefix="mine-test-"))
    try:
        for fn in tests:
            root = tmp / fn.__name__ / "repo"
            home = tmp / fn.__name__ / "home"
            root.mkdir(parents=True); home.mkdir(parents=True)
            m = load_miner(root, root)
            params = inspect.signature(fn).parameters
            kwargs = {}
            needs_home = "monkey_home" in params
            if needs_home:
                # find_session_files() resolves ~/.claude/projects via Path.home()
                m.Path.home = staticmethod(lambda: home)
                kwargs["monkey_home"] = home
            try:
                fn(m, root, **kwargs)
                print(f"  ok   {fn.__name__}")
            except Exception as e:
                failed.append(fn.__name__)
                print(f"  FAIL {fn.__name__}: {type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
