#!/usr/bin/env python3
"""Regression tests for context-check.py — run: python3 .claude/project-map/test_context_check.py

Stdlib assert + __main__, same shape as the sibling suites. Every check is proven
to DETECT something (a seeded bad input) as well as to pass a good one: a check
that only ever prints PASS is indistinguishable from one that checks nothing.

Every fixture is a temp project passed via --project-root, so nothing here reads
or writes the real repo (#18).
"""
from __future__ import annotations

import inspect
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "context-check.py"
REPO = HERE.parent.parent

GOOD_RULES = "# Rules\n\n- NEVER do the bad thing — it breaks. → `.documentation/a.md`\n"


def make_project(root: Path, claude_md: str = "# Project\n", rules: dict[str, str] | None = None) -> Path:
    (root / ".documentation").mkdir(parents=True, exist_ok=True)
    (root / ".documentation/a.md").write_text("# A\n")
    (root / "CLAUDE.md").write_text(claude_md)
    (root / ".claude/rules").mkdir(parents=True, exist_ok=True)
    for name, text in (rules or {}).items():
        (root / ".claude/rules" / name).write_text(text)
    return root


def check(root: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--project-root", str(root), *flags],
                          capture_output=True, text=True)


# ── budget ───────────────────────────────────────────────────────────────────

def test_under_budget_passes(tmp):
    r = check(make_project(tmp, rules={"r.md": GOOD_RULES}))
    assert r.returncode == 0, r.stdout


def test_over_budget_fails_and_names_the_file(tmp):
    make_project(tmp, rules={"huge.md": "x" * 2_000})
    r = check(tmp, "--budget", "1000")
    assert r.returncode == 1, r.stdout
    assert "FAIL  auto-loaded context is under 1,000" in r.stdout
    assert ".claude/rules/huge.md" in r.stdout


def test_budget_counts_nested_rules_and_dot_claude_claude_md(tmp):
    make_project(tmp)
    (tmp / ".claude/rules/sub").mkdir()
    (tmp / ".claude/rules/sub/deep.md").write_text("y" * 600)
    (tmp / ".claude/CLAUDE.md").write_text("z" * 600)
    r = check(tmp, "--budget", "1000")
    assert r.returncode == 1, r.stdout
    assert ".claude/rules/sub/deep.md" in r.stdout and ".claude/CLAUDE.md" in r.stdout


def test_warn_only_exits_zero(tmp):
    r = check(make_project(tmp, rules={"huge.md": "x" * 2_000}), "--budget", "1000", "--warn-only")
    assert r.returncode == 0 and "FAIL" in r.stdout, r.stdout


# ── pointers ─────────────────────────────────────────────────────────────────

def test_dangling_arrow_pointer_fails(tmp):
    r = check(make_project(tmp, rules={"r.md": "- NEVER x — y. → `.documentation/gone.md`\n"}))
    assert r.returncode == 1 and ".documentation/gone.md" in r.stdout, r.stdout


def test_dangling_backticked_doc_path_fails(tmp):
    r = check(make_project(tmp, claude_md="See `.documentation/missing/doc.md` for more.\n"))
    assert r.returncode == 1 and "missing/doc.md" in r.stdout, r.stdout


def test_dangling_markdown_link_fails_relative_to_the_file(tmp):
    # This repo's runbook links docs this way — the fork's regexes never saw them.
    make_project(tmp, rules={"r.md": "[doc](../../.documentation/a.md) and [bad](../../.documentation/nope.md)\n"})
    r = check(tmp)
    assert r.returncode == 1, r.stdout
    assert "nope.md" in r.stdout and "a.md" not in r.stdout.split("--")[-1], r.stdout


def test_root_relative_link_in_dot_claude_is_accepted(tmp):
    # The installer writes exactly this into .claude/CLAUDE.md. Strictly file-relative,
    # it blocked the first commit of every fresh install.
    make_project(tmp)
    (tmp / ".claude/project-map").mkdir()
    (tmp / ".claude/project-map/PROJECT_MAP.md").write_text("# Map\n")
    (tmp / ".claude/CLAUDE.md").write_text("[map](.claude/project-map/PROJECT_MAP.md)\n")
    r = check(tmp)
    assert r.returncode == 0, r.stdout


def test_anchor_url_and_code_fence_are_not_false_alarms(tmp):
    make_project(tmp, claude_md=(
        "→ `.documentation/a.md#section`\n"
        "[site](https://example.com/x.md) [mail](mailto:a@b.c) [here](#top)\n"
        "```md\n→ `.documentation/example-only.md`\n[x](nowhere.md)\n```\n"
    ))
    r = check(tmp)
    assert r.returncode == 0, r.stdout


# ── rule lines (--map-style) ─────────────────────────────────────────────────

def test_rule_lines_ignored_without_map_style(tmp):
    r = check(make_project(tmp, rules={"r.md": "- just some context\n"}))
    assert r.returncode == 0 and "ALWAYS/NEVER" not in r.stdout, r.stdout


def test_context_line_in_rules_file_fails(tmp):
    r = check(make_project(tmp, rules={"r.md": "- run the gates first → `.documentation/a.md`\n"}), "--map-style")
    assert r.returncode == 1 and "run the gates first" in r.stdout, r.stdout


def test_rule_without_pointer_fails(tmp):
    r = check(make_project(tmp, rules={"r.md": "- NEVER do it — because.\n"}), "--map-style")
    assert r.returncode == 1, r.stdout


def test_good_rule_line_passes(tmp):
    r = check(make_project(tmp, rules={"r.md": GOOD_RULES}), "--map-style")
    assert r.returncode == 0, r.stdout


def test_descriptive_files_are_exempt(tmp):
    make_project(tmp, rules={"operational-runbook.md": "- a trap, described\n"})
    assert check(tmp, "--map-style").returncode == 0
    r = check(tmp, "--map-style", "--descriptive", "other.md")
    assert r.returncode == 1, r.stdout


def test_claude_md_only_pointed_bullets_must_be_rules(tmp):
    make_project(tmp, claude_md="- `run it` with docker\n")
    assert check(tmp, "--map-style").returncode == 0
    (tmp / "CLAUDE.md").write_text("- a tool line → `.documentation/a.md`\n")
    assert check(tmp, "--map-style").returncode == 1


# ── wiring ───────────────────────────────────────────────────────────────────

def test_this_repo_passes():
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stdout


def _block(text: str) -> str:
    start = text.index("# ── Context Check")
    end = text.index("# ── End Context Check")
    return text[start:end]


def test_installer_writes_the_same_hook_block():
    assert _block((REPO / ".githooks/pre-commit").read_text()) == _block((REPO / ".claude/install.sh").read_text())


def test_hooks_are_committed_executable():
    # Git silently skips a non-executable hook. Until #20 both were committed 100644,
    # so no clone of this repo ever ran its pre-commit hook.
    out = subprocess.run(["git", "ls-files", "-s", ".githooks/"], capture_output=True, text=True,
                         cwd=REPO, check=True).stdout
    modes = {line.split("\t")[1]: line.split()[0] for line in out.splitlines()}
    assert modes and all(m == "100755" for m in modes.values()), modes


def test_hook_blocks_a_bad_rules_commit(tmp):
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.hooksPath=.githooks"]
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    make_project(tmp, rules={"r.md": GOOD_RULES})
    (tmp / ".githooks").mkdir()
    shutil.copy(REPO / ".githooks/pre-commit", tmp / ".githooks/pre-commit")
    (tmp / ".githooks/pre-commit").chmod(0o755)  # the mode itself is test_hooks_are_committed_executable's job
    (tmp / ".claude/project-map").mkdir(parents=True)
    shutil.copy(SCRIPT, tmp / ".claude/project-map/context-check.py")
    commit = lambda msg: subprocess.run(git + ["commit", "-qm", msg], cwd=tmp, capture_output=True, text=True)

    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
    r = commit("good")
    assert r.returncode == 0, r.stdout + r.stderr

    (tmp / ".claude/rules/r.md").write_text("- NEVER x — y. → `.documentation/gone.md`\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
    r = commit("bad")
    assert r.returncode != 0, "hook let a dangling pointer through"
    assert "Commit blocked" in r.stderr, r.stderr


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = []
    base = Path(tempfile.mkdtemp(prefix="context-check-test-"))
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
