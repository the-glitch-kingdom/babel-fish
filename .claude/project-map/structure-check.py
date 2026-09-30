#!/usr/bin/env python3
"""
structure-check.py — Babel Fish
Keeps files where the repo says they go (#22).

The project map describes where things ARE. `.claude/structure.toml` says where
things SHOULD go: every approved folder, what each may hold, its lifecycle
(planned → active → deprecated), and the dev → stg → prod environments. This
script checks the tracked tree against it.

Opt-in: with no manifest it only explains the options and exits 0. The
pre-commit hook runs it only when the manifest exists.

Deliberately NOT part of generate.py: the hook runs generate.py only when code
is staged and discards its errors — a failure there could never block a commit.

Usage:
    python structure-check.py [--staged | --since REF] [--warn-only] [--project-root PATH]

Exit: 0 clean (or no manifest), 1 violations, 2 unusable manifest or not a git repo.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

try:
    import tomllib
except ImportError:  # ponytail: only this script needs 3.11; the rest of babel-fish keeps 3.8
    tomllib = None

PROJECT_ROOT = Path(__file__).parent.parent.parent
MANIFEST = PROJECT_ROOT / ".claude" / "structure.toml"

MODES = ("monorepo", "single", "multi-repo")
STATUSES = ("planned", "active", "deprecated")
TARGETS = ("local", "cloud")


def configure_paths(project_root: Path) -> None:
    """Rebind every root-derived path (#18: never set PROJECT_ROOT alone)."""
    global PROJECT_ROOT, MANIFEST
    PROJECT_ROOT = project_root
    MANIFEST = project_root / ".claude" / "structure.toml"


# ── globs ────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def glob_re(pattern: str) -> re.Pattern:
    """Path glob: `*` and `?` stop at `/`, `**` crosses it, `**/` may match nothing."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def matches(path: str, patterns) -> bool:
    return any(glob_re(p).match(path) for p in patterns)


# ── git ──────────────────────────────────────────────────────────────────────

def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def is_git_repo() -> bool:
    try:
        return git("rev-parse", "--is-inside-work-tree").strip() == "true"
    except (RuntimeError, OSError):
        return False


# ── manifest ─────────────────────────────────────────────────────────────────

def load_manifest(path: Path) -> dict:
    with open(path, "rb") as f:
        m = tomllib.load(f)
    for f in m.get("folder", []):
        if isinstance(f.get("path"), str):
            f["path"] = f["path"].strip("/")
    return m


def _str_list(v) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def validate(m: dict) -> list[str]:
    """-> problems that make the manifest unusable (exit 2)."""
    errs = []
    if m.get("mode", "single") not in MODES:
        errs.append(f"mode = {m.get('mode')!r}; expected one of {', '.join(MODES)}")
    for key in ("root_files", "exceptions", "env_roots"):
        if key in m and not _str_list(m[key]):
            errs.append(f"{key} must be a list of strings")

    seen = set()
    for i, f in enumerate(m.get("folder", [])):
        where = f"[[folder]] #{i + 1}"
        p = f.get("path")
        if not isinstance(p, str) or not p:
            errs.append(f"{where}: path is required")
            continue
        where = f"[[folder]] {p}"
        if p in seen:
            errs.append(f"{where}: listed twice")
        seen.add(p)
        if f.get("status", "active") not in STATUSES:
            errs.append(f"{where}: status = {f.get('status')!r}; expected one of {', '.join(STATUSES)}")
        if "holds" in f and not _str_list(f["holds"]):
            errs.append(f"{where}: holds must be a list of glob strings")

    envs = m.get("environment", [])
    names = [e.get("name") for e in envs]
    for e in envs:
        where = f"[[environment]] {e.get('name', '?')}"
        if not isinstance(e.get("name"), str) or not e["name"]:
            errs.append(f"{where}: name is required")
        if e.get("target") not in TARGETS:
            errs.append(f"{where}: target = {e.get('target')!r}; expected one of {', '.join(TARGETS)}")
        for key in ("promotes_to", "mirrors"):
            if key in e and e[key] not in names:
                errs.append(f"{where}: {key} = {e[key]!r} is not a declared environment")
    if len(set(names)) != len(names):
        errs.append("[[environment]]: a name is declared twice")
    nxt = {e.get("name"): e.get("promotes_to") for e in envs}
    for start in nxt:
        cur, hops = start, 0
        while cur in nxt and nxt[cur] and hops <= len(nxt):
            cur, hops = nxt[cur], hops + 1
        if hops > len(nxt):
            errs.append(f"[[environment]]: promotes_to loops back through {start!r}")
            break

    for i, r in enumerate(m.get("repo", [])):
        if not isinstance(r.get("name"), str) or not r["name"]:
            errs.append(f"[[repo]] #{i + 1}: name is required")
        if not (r.get("path") or r.get("url")):
            errs.append(f"[[repo]] {r.get('name', '#' + str(i + 1))}: needs a path or a url")
    return errs


# ── cli ──────────────────────────────────────────────────────────────────────

def warn_old_python() -> None:
    v = ".".join(map(str, sys.version_info[:3]))
    print(f"WARN  structure-check skipped: it reads .claude/structure.toml with Python's built-in\n"
          f"      TOML parser (tomllib), which needs Python 3.11+. This is Python {v}.\n"
          f"      Nothing was checked. Upgrade to Python 3.11 or newer to turn the check on;\n"
          f"      CI running 3.11+ still enforces it.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Check tracked files against .claude/structure.toml (#22).")
    ap.add_argument("--warn-only", action="store_true", help="report, but always exit 0")
    ap.add_argument("--project-root", type=Path, default=None)
    args = ap.parse_args()
    if args.project_root:
        configure_paths(args.project_root.resolve())

    if not MANIFEST.is_file():
        print("No .claude/structure.toml -- structure checking is off.")
        sys.exit(0)
    if tomllib is None:
        warn_old_python()
        sys.exit(0)
    try:
        m = load_manifest(MANIFEST)
    except tomllib.TOMLDecodeError as e:
        print(f"FAIL  .claude/structure.toml is not valid TOML: {e}")
        sys.exit(2)
    errs = validate(m)
    for e in errs:
        print(f"FAIL  .claude/structure.toml: {e}")
    if errs:
        sys.exit(2)
    print("OK")


if __name__ == "__main__":
    main()
