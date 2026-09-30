#!/usr/bin/env python3
"""Regression tests for structure-check.py — run: python3 .claude/project-map/test_structure_check.py

Stdlib assert + __main__, same shape as the sibling suites. Every rule is proven
to DETECT a seeded violation as well as to pass a clean tree.

Every fixture is a temp git repo passed via --project-root, so nothing here reads
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
SCRIPT = HERE / "structure-check.py"
REPO = HERE.parent.parent

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]

BASE_MANIFEST = '''
mode = "single"
root_files = ["README.md"]

[[folder]]
path = "src"
purpose = "Application source"
holds = ["**/*.py"]
status = "active"
'''


def make_repo(root: Path, files: dict[str, str], manifest: str | None = BASE_MANIFEST,
              commit: bool = True) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    if manifest is not None:
        (root / ".claude").mkdir(exist_ok=True)
        (root / ".claude/structure.toml").write_text(manifest)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    if commit:
        subprocess.run(GIT + ["commit", "-qm", "init"], cwd=root, check=True)
    return root


def check(root: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--project-root", str(root), *flags],
                          capture_output=True, text=True)


def with_manifest(extra: str) -> str:
    return BASE_MANIFEST + extra


# ── manifest ─────────────────────────────────────────────────────────────────

def test_no_manifest_is_off_not_a_failure(tmp):
    r = check(make_repo(tmp, {"README.md": "x"}, manifest=None))
    assert r.returncode == 0, r.stdout
    assert "structure.toml" in r.stdout, r.stdout


def test_valid_manifest_loads(tmp):
    r = check(make_repo(tmp, {"README.md": "x", "src/a.py": "x"}))
    assert r.returncode == 0, r.stdout + r.stderr


def test_invalid_toml_exits_2(tmp):
    r = check(make_repo(tmp, {"README.md": "x"}, manifest="mode = \n"))
    assert r.returncode == 2 and "not valid TOML" in r.stdout, r.stdout


def test_bad_status_exits_2(tmp):
    m = BASE_MANIFEST.replace('status = "active"', 'status = "retired"')
    r = check(make_repo(tmp, {"README.md": "x"}, manifest=m))
    assert r.returncode == 2 and "retired" in r.stdout, r.stdout


def test_bad_mode_exits_2(tmp):
    r = check(make_repo(tmp, {"README.md": "x"}, manifest='mode = "polyrepo"\n'))
    assert r.returncode == 2 and "polyrepo" in r.stdout, r.stdout


def test_duplicate_folder_exits_2(tmp):
    r = check(make_repo(tmp, {"README.md": "x"}, manifest=with_manifest('[[folder]]\npath = "src/"\n')))
    assert r.returncode == 2 and "listed twice" in r.stdout, r.stdout


def test_env_pointing_at_undeclared_env_exits_2(tmp):
    m = with_manifest('[[environment]]\nname = "dev"\ntarget = "local"\npromotes_to = "qa"\n')
    r = check(make_repo(tmp, {"README.md": "x"}, manifest=m))
    assert r.returncode == 2 and "'qa' is not a declared environment" in r.stdout, r.stdout


def test_promotion_cycle_exits_2(tmp):
    m = with_manifest('[[environment]]\nname = "a"\ntarget = "cloud"\npromotes_to = "b"\n'
                      '[[environment]]\nname = "b"\ntarget = "cloud"\npromotes_to = "a"\n')
    r = check(make_repo(tmp, {"README.md": "x"}, manifest=m))
    assert r.returncode == 2 and "loops" in r.stdout, r.stdout


def test_bad_env_target_exits_2(tmp):
    m = with_manifest('[[environment]]\nname = "dev"\ntarget = "laptop"\n')
    r = check(make_repo(tmp, {"README.md": "x"}, manifest=m))
    assert r.returncode == 2 and "laptop" in r.stdout, r.stdout


def test_repo_pointer_needs_path_or_url(tmp):
    r = check(make_repo(tmp, {"README.md": "x"}, manifest=with_manifest('[[repo]]\nname = "api"\n')))
    assert r.returncode == 2 and "needs a path or a url" in r.stdout, r.stdout


def test_old_python_warns_and_skips(tmp):
    """Python < 3.11 has no tomllib: a readable WARN, exit 0, never a block."""
    make_repo(tmp, {"README.md": "x"})
    code = ("import sys, runpy; sys.modules['tomllib'] = None; "
            f"sys.argv = ['structure-check.py', '--project-root', {str(tmp)!r}]; "
            f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WARN" in r.stdout and "3.11" in r.stdout and "Nothing was checked" in r.stdout, r.stdout


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = []
    base = Path(tempfile.mkdtemp(prefix="structure-check-test-"))
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
