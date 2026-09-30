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

# Environments. An env folder is <env_root>/<env name>/; siblings named below hold
# what every environment shares (base + overlay).
DEFAULT_ENV_ROOTS = ["infra/env", "infra/deploy"]
SHARED_ENV_DIRS = {"base", "shared", "common", "modules"}
ENV_PARENT_DIRS = {"env", "envs", "environments", "overlays"}  # <parent>/<env>/ outside env_roots
MIGRATION_DIRS = {"migrations", "migration", "alembic"}
SECRET_OK_SUFFIXES = (".example", ".sample", ".template", ".dist")  # .env.example, .env.prod.example ...
# ponytail: fixed lists — extend here when a real repo needs another platform
LOCAL_ONLY = ["**/*compose*.yml", "**/*compose*.yaml", "**/seed*", "**/seeds/**",
              "**/fixtures/**", "**/*.pem", "**/*.crt", "**/*.key"]
DEPLOY_ONLY = ["**/*.tf", "**/*.tfvars", "**/*.hcl", "**/kustomization.yaml", "**/kustomization.yml",
               "**/Chart.yaml", "**/fly.toml", "**/render.yaml", "**/vercel.json", "**/railway.json"]
EMPTY_BLOB = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"  # identical empty files are not copies


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


# ── checks ───────────────────────────────────────────────────────────────────

def tracked() -> dict[str, str]:
    """-> {path: blob sha} for every file in the index (what the next commit holds)."""
    out = {}
    for entry in git("ls-files", "-s", "-z").split("\0"):
        if entry:
            meta, path = entry.split("\t", 1)
            out[path] = meta.split()[1]
    return out


def added(staged: bool, since: str | None) -> set[str]:
    """-> paths new in this change: staged adds, or adds since REF (CI). Renames count as adds."""
    if staged:
        out = git("diff", "--cached", "--name-only", "--no-renames", "--diff-filter=A", "-z")
    elif since:
        out = git("diff", "--name-only", "--no-renames", "--diff-filter=A", "-z", f"{since}...HEAD")
    else:
        return set()
    return {p for p in out.split("\0") if p}


class Finding:
    def __init__(self, level: str, path: str, msg: str, exemptable: bool = True):
        self.level, self.path, self.msg, self.exemptable = level, path, msg, exemptable


def owner(path: str, folders: list[dict]) -> dict | None:
    """-> the deepest manifest folder containing `path` (folders pre-sorted deepest first)."""
    for f in folders:
        if path.startswith(f["path"] + "/"):
            return f
    return None


def check_folders(m: dict, files: dict[str, str], new: set[str]) -> list[Finding]:
    folders = sorted(m.get("folder", []), key=lambda f: -f["path"].count("/") - len(f["path"]))
    root_files = m.get("root_files", [])
    out, used = [], set()
    for path in sorted(files):
        if path == ".claude/structure.toml":  # the manifest never has to list itself
            continue
        f = owner(path, folders)
        if f is None:
            if "/" not in path:
                if not matches(path, root_files):
                    out.append(Finding("FAIL", path, "root file not in root_files -- add it there, or move it into a folder"))
            else:
                out.append(Finding("FAIL", path, "under no manifest folder -- move it into one, or add a [[folder]] for it"))
            continue
        used.add(f["path"])
        rel = path[len(f["path"]) + 1:]
        if "holds" in f and not matches(rel, f["holds"]):
            out.append(Finding("FAIL", path, f"doesn't match {f['path']}/ holds {f['holds']} -- move it, or widen holds"))
        if f.get("status") == "deprecated" and path in new:
            out.append(Finding("FAIL", path, f"new file in deprecated folder {f['path']}/ -- put it where its replacement lives"))

    for f in folders:
        status, p = f.get("status", "active"), f["path"]
        if status == "planned" and p in used:
            out.append(Finding("WARN", p + "/", "planned folder now has files -- set status = \"active\""))
        elif status == "active" and p not in used:
            out.append(Finding("WARN", p + "/", "active folder has no tracked files -- planned, or finished retiring?"))
        elif status == "deprecated" and p not in used:
            out.append(Finding("WARN", p + "/", "deprecated folder is empty -- remove its [[folder]] entry (and the folder) in one commit"))
    return out


def check_secrets(files: dict[str, str]) -> list[Finding]:
    """A real .env is never committed, in any mode, and no exception can allow it."""
    out = []
    for path in files:
        name = path.rsplit("/", 1)[-1]
        if name.endswith(SECRET_OK_SUFFIXES) or not (name == ".env" or name.startswith(".env.") or name.endswith(".env")):
            continue
        out.append(Finding("FAIL", path, "secrets file is tracked -- git rm --cached it, keep values in "
                           "the environment or a secret manager, commit only .env.example", exemptable=False))
    return out


def check_environments(m: dict, files: dict[str, str]) -> list[Finding]:
    """dev → stg → prod: declared envs only, deltas only, stg mirrors prod, local vs cloud kept apart."""
    envs = {e["name"]: e for e in m.get("environment", [])}
    if not envs:
        return []
    roots = [r.strip("/") for r in m.get("env_roots", DEFAULT_ENV_ROOTS)]
    out, undeclared = [], set()
    env_files: dict[tuple[str, str], set[str]] = {}  # (root, env) -> paths relative to root/env
    in_env = set()

    for path in sorted(files):
        root = next((r for r in roots if path.startswith(r + "/")), None)
        parts = path.split("/")
        dirs = parts[:-1]
        if root is None:
            for i in range(1, len(dirs)):
                if dirs[i] in envs and dirs[i - 1] in ENV_PARENT_DIRS:
                    d = "/".join(dirs[:i + 1])
                    if d not in undeclared:
                        undeclared.add(d)
                        out.append(Finding("FAIL", d + "/", f"per-environment folder outside env_roots {roots} -- "
                                           f"move its deltas to <env_root>/{dirs[i]}/, or add its parent to env_roots"))
            if set(dirs) & MIGRATION_DIRS and set(dirs) & set(envs):
                out.append(Finding("FAIL", path, "per-environment migration -- migrations are shared: one folder, "
                                   "the same path forward in every environment"))
            continue
        sub = path[len(root) + 1:]
        if "/" not in sub:
            continue  # shared file directly in the env root
        env, rel = sub.split("/", 1)
        if env in SHARED_ENV_DIRS:
            continue
        if env not in envs:
            d = f"{root}/{env}"
            if d not in undeclared:
                undeclared.add(d)
                out.append(Finding("FAIL", d + "/", f"environment {env!r} is not declared -- add an [[environment]], "
                                   "or fold it into a declared one"))
            continue
        in_env.add(path)
        env_files.setdefault((root, env), set()).add(rel)
        target = envs[env]["target"]
        if target == "cloud" and matches(rel, LOCAL_ONLY):
            out.append(Finding("FAIL", path, f"local-only file in cloud environment {env!r} -- compose overrides, "
                               "seeds and local certs belong to a local environment"))
        elif target == "local" and matches(rel, DEPLOY_ONLY):
            out.append(Finding("FAIL", path, f"deploy config in local environment {env!r} -- Terraform, k8s and "
                               "platform files belong to a cloud environment"))
        if set(rel.split("/")[:-1]) & MIGRATION_DIRS:
            out.append(Finding("FAIL", path, "per-environment migration -- migrations are shared: one folder, "
                               "the same path forward in every environment"))

    for e in envs.values():
        m_env = e.get("mirrors")
        if not m_env:
            continue
        for root in roots:
            a, b = env_files.get((root, e["name"]), set()), env_files.get((root, m_env), set())
            for rel in sorted(b - a):
                out.append(Finding("FAIL", f"{root}/{e['name']}/{rel}", f"missing: {e['name']} mirrors {m_env}, "
                                   f"which has {root}/{m_env}/{rel} -- add it, or remove it from {m_env}"))
            for rel in sorted(a - b):
                out.append(Finding("FAIL", f"{root}/{m_env}/{rel}", f"missing: {e['name']} mirrors {m_env} and has "
                                   f"{root}/{e['name']}/{rel} -- add it to {m_env}, or remove it from {e['name']}"))

    shared = {sha: p for p, sha in files.items() if p not in in_env and sha != EMPTY_BLOB}
    for path in sorted(in_env):
        if files[path] in shared:
            out.append(Finding("FAIL", path, f"identical copy of {shared[files[path]]} -- an environment folder "
                               "holds only what differs; reference the shared file instead"))

    token = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(map(re.escape, envs)) + r")(?![A-Za-z0-9])")
    groups: dict[str, list[str]] = {}
    for path in files:
        if path.startswith(".github/workflows/") and token.search(path):
            groups.setdefault(token.sub("{env}", path), []).append(path)
    for tmpl, paths in sorted(groups.items()):
        if len(paths) > 1:
            out.append(Finding("WARN", tmpl, f"per-environment workflow copies ({', '.join(sorted(paths))}) -- "
                               "prefer one workflow that takes the environment as input"))
    return out


def check_repos(m: dict) -> list[Finding]:
    out = []
    for r in m.get("repo", []):
        if r.get("path") and not (PROJECT_ROOT / r["path"] / ".git").exists():
            out.append(Finding("WARN", r["path"], f"[[repo]] {r['name']}: no git checkout here -- clone it or fix the path"))
    return out


def apply_exceptions(findings: list[Finding], exceptions: list[str]) -> tuple[list[Finding], int]:
    """Drop FAILs the baseline allows; WARN on baseline entries that allow nothing anymore."""
    kept, hit, baselined = [], set(), 0
    for f in findings:
        pats = [e for e in exceptions if f.level == "FAIL" and f.exemptable and glob_re(e).match(f.path)]
        if pats:
            hit.update(pats)
            baselined += 1
        else:
            kept.append(f)
    for e in exceptions:
        if e not in hit:
            kept.append(Finding("WARN", e, "exception no longer needed -- remove it from exceptions"))
    return kept, baselined


def run(m: dict, staged: bool, since: str | None) -> int:
    """Print the report; return the number of FAILs."""
    files = tracked()
    findings = (check_folders(m, files, added(staged, since)) + check_environments(m, files)
                + check_secrets(files) + check_repos(m))
    findings, baselined = apply_exceptions(findings, m.get("exceptions", []))
    fails = [f for f in findings if f.level == "FAIL"]
    warns = [f for f in findings if f.level == "WARN"]

    print(f"structure-check -- .claude/structure.toml (mode: {m.get('mode', 'single')})")
    for f in fails + warns:
        print(f"  {f.level}  {f.path}  -- {f.msg.split(' -- ', 1)[0]}")
        if " -- " in f.msg:
            print(f"        fix: {f.msg.split(' -- ', 1)[1]}")
    print(f"\n{len(files)} files checked" + (f", {baselined} allowed by exceptions" if baselined else ""))
    print("OK" if not fails else f"{len(fails)} FAILED")
    return len(fails)


# ── cli ──────────────────────────────────────────────────────────────────────

def warn_old_python() -> None:
    v = ".".join(map(str, sys.version_info[:3]))
    print(f"WARN  structure-check skipped: it reads .claude/structure.toml with Python's built-in\n"
          f"      TOML parser (tomllib), which needs Python 3.11+. This is Python {v}.\n"
          f"      Nothing was checked. Upgrade to Python 3.11 or newer to turn the check on;\n"
          f"      CI running 3.11+ still enforces it.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Check tracked files against .claude/structure.toml (#22).")
    new = ap.add_mutually_exclusive_group()
    new.add_argument("--staged", action="store_true",
                     help="treat staged additions as new files (pre-commit)")
    new.add_argument("--since", metavar="REF",
                     help="treat files added since REF as new (CI, e.g. --since origin/main)")
    ap.add_argument("--warn-only", action="store_true", help="report, but always exit 0")
    ap.add_argument("--project-root", type=Path, default=None)
    args = ap.parse_args()
    if args.project_root:
        configure_paths(args.project_root.resolve())

    if not is_git_repo():
        print(f"FAIL  {PROJECT_ROOT} is not a git repository -- structure-check reads the git index (git init first)")
        sys.exit(2)
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
    try:
        fails = run(m, args.staged, args.since)
    except RuntimeError as e:
        print(f"FAIL  {e}")
        sys.exit(2)
    sys.exit(1 if fails and not args.warn_only else 0)


if __name__ == "__main__":
    main()
