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


def test_not_a_git_repo_exits_2(tmp):
    (tmp / ".claude").mkdir()
    (tmp / ".claude/structure.toml").write_text(BASE_MANIFEST)
    r = check(tmp)
    assert r.returncode == 2 and "not a git repository" in r.stdout, r.stdout


# ── folders ──────────────────────────────────────────────────────────────────

def test_clean_tree_passes(tmp):
    r = check(make_repo(tmp, {"README.md": "x", "src/a.py": "x", "src/pkg/b.py": "x"}))
    assert r.returncode == 0 and "OK" in r.stdout, r.stdout


def test_path_under_no_folder_fails(tmp):
    r = check(make_repo(tmp, {"README.md": "x", "tools/x.py": "x"}))
    assert r.returncode == 1 and "tools/x.py" in r.stdout and "under no manifest folder" in r.stdout, r.stdout


def test_root_file_not_listed_fails(tmp):
    r = check(make_repo(tmp, {"README.md": "x", "notes.txt": "x"}))
    assert r.returncode == 1 and "notes.txt" in r.stdout and "root_files" in r.stdout, r.stdout


def test_root_files_accept_globs(tmp):
    m = BASE_MANIFEST.replace('root_files = ["README.md"]', 'root_files = ["README.md", "*.lock"]')
    r = check(make_repo(tmp, {"README.md": "x", "poetry.lock": "x"}, manifest=m))
    assert r.returncode == 0, r.stdout


def test_file_outside_holds_fails(tmp):
    r = check(make_repo(tmp, {"README.md": "x", "src/a.py": "x", "src/compose.yml": "x"}))
    assert r.returncode == 1 and "src/compose.yml" in r.stdout and "holds" in r.stdout, r.stdout


def test_deepest_folder_wins(tmp):
    m = with_manifest('[[folder]]\npath = "src/assets"\nholds = ["*.png"]\n')
    r = check(make_repo(tmp, {"README.md": "x", "src/assets/logo.png": "x"}, manifest=m))
    assert r.returncode == 0, r.stdout  # src's holds (*.py) must not apply to src/assets
    r = check(make_repo(tmp / "b", {"README.md": "x", "src/assets/x.py": "x"}, manifest=m))
    assert r.returncode == 1 and "src/assets/x.py" in r.stdout, r.stdout


DEPRECATED = with_manifest('[[folder]]\npath = "legacy"\nstatus = "deprecated"\n')


def test_existing_file_in_deprecated_folder_passes(tmp):
    r = check(make_repo(tmp, {"README.md": "x", "legacy/old.py": "x"}, manifest=DEPRECATED), "--staged")
    assert r.returncode == 0, r.stdout


def test_new_staged_file_in_deprecated_folder_fails(tmp):
    make_repo(tmp, {"README.md": "x", "legacy/old.py": "x"}, manifest=DEPRECATED)
    (tmp / "legacy/new.py").write_text("x")
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
    r = check(tmp, "--staged")
    assert r.returncode == 1 and "legacy/new.py" in r.stdout and "deprecated" in r.stdout, r.stdout
    assert "legacy/old.py" not in r.stdout, r.stdout


def test_since_ref_catches_new_file_in_deprecated_folder(tmp):
    make_repo(tmp, {"README.md": "x", "legacy/old.py": "x"}, manifest=DEPRECATED)
    subprocess.run(["git", "checkout", "-qb", "feature"], cwd=tmp, check=True)
    (tmp / "legacy/new.py").write_text("x")
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
    subprocess.run(GIT + ["commit", "-qm", "add"], cwd=tmp, check=True)
    r = check(tmp, "--since", "main")
    assert r.returncode == 1 and "legacy/new.py" in r.stdout, r.stdout
    assert check(tmp).returncode == 0  # without a diff base nothing is "new"


def test_empty_deprecated_folder_warns(tmp):
    r = check(make_repo(tmp, {"README.md": "x"}, manifest=DEPRECATED))
    assert r.returncode == 0 and "WARN  legacy/" in r.stdout and "remove" in r.stdout, r.stdout


def test_planned_folder_with_files_warns(tmp):
    m = with_manifest('[[folder]]\npath = "docs"\nstatus = "planned"\n')
    r = check(make_repo(tmp, {"README.md": "x", "docs/a.md": "x"}, manifest=m))
    assert r.returncode == 0 and "WARN  docs/" in r.stdout and "active" in r.stdout, r.stdout


def test_exceptions_allow_known_violations(tmp):
    m = BASE_MANIFEST.replace('root_files', 'exceptions = ["tools/**"]\nroot_files')
    r = check(make_repo(tmp, {"README.md": "x", "tools/x.py": "x"}, manifest=m))
    assert r.returncode == 0 and "1 allowed by exceptions" in r.stdout, r.stdout


def test_stale_exception_warns(tmp):
    m = BASE_MANIFEST.replace('root_files', 'exceptions = ["gone/**"]\nroot_files')
    r = check(make_repo(tmp, {"README.md": "x"}, manifest=m))
    assert r.returncode == 0 and "WARN  gone/**" in r.stdout and "no longer needed" in r.stdout, r.stdout


def test_warn_only_exits_zero(tmp):
    r = check(make_repo(tmp, {"README.md": "x", "tools/x.py": "x"}), "--warn-only")
    assert r.returncode == 0 and "FAIL" in r.stdout, r.stdout


def test_repo_pointer_without_checkout_warns(tmp):
    m = with_manifest('[[repo]]\nname = "api"\npath = "../api"\n')
    r = check(make_repo(tmp / "web", {"README.md": "x"}, manifest=m))
    assert r.returncode == 0 and "WARN  ../api" in r.stdout, r.stdout
    subprocess.run(["git", "init", "-q", str(tmp / "api")], check=True)
    assert "WARN  ../api" not in check(tmp / "web").stdout


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
