#!/usr/bin/env python3
"""Regression tests for structure-check.py — run: python3 .claude/project-map/test_structure_check.py

Stdlib assert + __main__, same shape as the sibling suites. Every rule is proven
to DETECT a seeded violation as well as to pass a clean tree.

Every fixture is a temp git repo passed via --project-root, so nothing here reads
or writes the real repo (#18).
"""
from __future__ import annotations

import inspect
import json
import re
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


# ── environments ─────────────────────────────────────────────────────────────

ENV_MANIFEST = '''
mode = "monorepo"
root_files = ["README.md"]

[[folder]]
path = "infra"

[[folder]]
path = "apps"

[[folder]]
path = "migrations"

[[folder]]
path = ".github"

[[environment]]
name = "dev"
target = "local"
promotes_to = "stg"

[[environment]]
name = "stg"
target = "cloud"
promotes_to = "prod"
mirrors = "prod"

[[environment]]
name = "prod"
target = "cloud"
'''

ENV_TREE = {
    "README.md": "x",
    "infra/env/dev/.env.example": "A=dev\n",
    "infra/env/stg/.env.example": "A=stg\n",
    "infra/env/prod/.env.example": "A=prod\n",
    "infra/compose/base.yml": "services: {}\n",
    "infra/deploy/base/main.tf": "module {}\n",
    "infra/deploy/stg/main.tf": "env = stg\n",
    "infra/deploy/prod/main.tf": "env = prod\n",
    "apps/api/main.py": "x",
    "migrations/001_init.sql": "x",
}


def env_add(tmp: Path, files: dict[str, str]) -> subprocess.CompletedProcess:
    tree = {**ENV_TREE, **files}
    return check(make_repo(tmp, tree, manifest=ENV_MANIFEST))


def test_clean_environment_tree_passes(tmp):
    r = check(make_repo(tmp, ENV_TREE, manifest=ENV_MANIFEST))
    assert r.returncode == 0, r.stdout


def test_undeclared_environment_folder_fails(tmp):
    r = env_add(tmp, {"infra/env/qa/.env.example": "A=qa\n"})
    assert r.returncode == 1 and "infra/env/qa/" in r.stdout and "'qa' is not declared" in r.stdout, r.stdout


def test_stg_must_mirror_prod(tmp):
    r = env_add(tmp, {"infra/deploy/prod/redis.tf": "redis\n"})
    assert r.returncode == 1 and "infra/deploy/stg/redis.tf" in r.stdout and "mirrors prod" in r.stdout, r.stdout


def test_dev_is_exempt_from_parity(tmp):
    r = env_add(tmp, {"infra/env/dev/seed.sql": "dev seed\n"})
    assert r.returncode == 0, r.stdout


def test_local_only_file_in_cloud_env_fails(tmp):
    r = env_add(tmp, {"infra/env/prod/seed.sql": "p\n", "infra/env/stg/seed.sql": "s\n"})
    assert r.returncode == 1 and "infra/env/prod/seed.sql" in r.stdout and "local-only" in r.stdout, r.stdout


def test_deploy_file_in_local_env_fails(tmp):
    r = env_add(tmp, {"infra/deploy/dev/main.tf": "dev\n"})
    assert r.returncode == 1 and "infra/deploy/dev/main.tf" in r.stdout and "deploy config" in r.stdout, r.stdout


def test_identical_copy_of_shared_file_fails(tmp):
    r = env_add(tmp, {"infra/env/dev/base.yml": "services: {}\n"})
    assert r.returncode == 1 and "identical copy of infra/compose/base.yml" in r.stdout, r.stdout


def test_empty_files_are_not_copies(tmp):
    r = env_add(tmp, {"infra/env/dev/.gitkeep": "", "apps/api/.gitkeep": ""})
    assert r.returncode == 0, r.stdout


def test_per_environment_migrations_fail(tmp):
    r = env_add(tmp, {"migrations/prod/002.sql": "p\n"})
    assert r.returncode == 1 and "migrations/prod/002.sql" in r.stdout and "per-environment migration" in r.stdout
    r = env_add(tmp / "b", {"infra/env/dev/migrations/001.sql": "d\n"})
    assert r.returncode == 1 and "per-environment migration" in r.stdout, r.stdout


def test_per_app_env_folder_outside_env_roots_fails(tmp):
    r = env_add(tmp, {"apps/api/env/prod/.env.example": "A=1\n"})
    assert r.returncode == 1 and "apps/api/env/prod/" in r.stdout and "outside env_roots" in r.stdout, r.stdout


def test_custom_env_roots(tmp):
    m = ENV_MANIFEST.replace('root_files', 'env_roots = ["k8s/overlays"]\nroot_files') + '[[folder]]\npath = "k8s"\n'
    tree = {"README.md": "x", "k8s/overlays/stg/kustomization.yaml": "a", "k8s/overlays/prod/kustomization.yaml": "b"}
    assert check(make_repo(tmp, tree, manifest=m)).returncode == 0
    tree["k8s/overlays/prod/hpa.yaml"] = "c"
    r = check(make_repo(tmp / "b", tree, manifest=m))
    assert r.returncode == 1 and "k8s/overlays/stg/hpa.yaml" in r.stdout, r.stdout


def test_per_environment_workflow_copies_warn(tmp):
    r = env_add(tmp, {".github/workflows/deploy-stg.yml": "a", ".github/workflows/deploy-prod.yml": "b"})
    assert r.returncode == 0 and "deploy-{env}.yml" in r.stdout and "WARN" in r.stdout, r.stdout


def test_no_environments_declared_skips_env_rules(tmp):
    m = ENV_MANIFEST.split("[[environment]]")[0]
    tree = {**ENV_TREE, "infra/env/qa/x": "1", "infra/deploy/prod/redis.tf": "r"}
    assert check(make_repo(tmp, tree, manifest=m)).returncode == 0


# ── secrets ──────────────────────────────────────────────────────────────────

def test_tracked_env_file_fails_and_no_glob_can_except_it(tmp):
    m = BASE_MANIFEST.replace('root_files', 'exceptions = ["src/*", "**/.env"]\nroot_files').replace('["**/*.py"]', '["**"]')
    r = check(make_repo(tmp, {"README.md": "x", "src/.env": "SECRET=1"}, manifest=m))
    assert r.returncode == 1 and "secrets file is tracked" in r.stdout, r.stdout


def test_secret_fixture_can_be_excepted_by_exact_path_only(tmp):
    """Vendored test configs (.env.testing, .env.ci) are committed on purpose: the escape hatch
    is an exact path, so a NEW .env next to them still fails."""
    m = BASE_MANIFEST.replace('root_files', 'exceptions = ["src/.env.testing"]\nroot_files').replace('["**/*.py"]', '["**"]')
    root = make_repo(tmp, {"README.md": "x", "src/.env.testing": "APP_KEY=test"}, manifest=m)
    r = check(root)
    assert r.returncode == 0 and "1 allowed by exceptions" in r.stdout, r.stdout
    (root / "src/.env").write_text("SECRET=1")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = check(root)
    assert r.returncode == 1 and "FAIL  src/.env " in r.stdout and "src/.env.testing" not in r.stdout, r.stdout


def test_secret_variants_fail_examples_pass(tmp):
    m = BASE_MANIFEST.replace('["**/*.py"]', '["**"]')
    bad = {"src/.env.production": "x", "src/prod.env": "x"}
    ok = {"src/.env.example": "x", "src/.env.prod.example": "x", "src/.envrc": "x"}
    r = check(make_repo(tmp, {"README.md": "x", **bad, **ok}, manifest=m))
    assert r.returncode == 1, r.stdout
    for p in bad:
        assert f"FAIL  {p}" in r.stdout, r.stdout
    for p in ok:
        assert p not in r.stdout, r.stdout


# ── detect + bootstrap ───────────────────────────────────────────────────────
# Repos go in tmp/"r" so the parent holds no other git repo (sibling detection).

def detect(root: Path) -> dict:
    r = check(root, "--detect", "--json")
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def test_detect_single(tmp):
    d = detect(make_repo(tmp / "r", {"README.md": "x", "src/a.py": "x"}, manifest=None))
    assert d["mode"] == "single" and d["sibling_repos"] == [], d
    assert d["top_level"][0]["path"] == "src" and d["root_files"] == ["README.md"], d


def test_detect_monorepo_from_workspace_file(tmp):
    d = detect(make_repo(tmp / "r", {"pnpm-workspace.yaml": "packages: []", "apps/web/index.ts": "x"}, manifest=None))
    assert d["mode"] == "monorepo" and "pnpm-workspace.yaml" in d["reasons"][0], d


def test_detect_monorepo_from_package_json_workspaces(tmp):
    d = detect(make_repo(tmp / "r", {"package.json": '{"workspaces": ["apps/*"]}'}, manifest=None))
    assert d["mode"] == "monorepo", d


def test_detect_monorepo_from_two_packages(tmp):
    tree = {"apps/api/pyproject.toml": "x", "apps/web/package.json": "{}"}
    d = detect(make_repo(tmp / "r", tree, manifest=None))
    assert d["mode"] == "monorepo" and d["packages"] == ["apps/api", "apps/web"], d


def test_detect_multi_repo_from_sibling(tmp):
    subprocess.run(["git", "init", "-q", str(tmp / "other")], check=True)
    d = detect(make_repo(tmp / "r", {"README.md": "x"}, manifest=None))
    assert d["mode"] == "multi-repo" and d["sibling_repos"] == ["other"], d


def test_detect_environments(tmp):
    tree = {"infra/env/dev/.env.example": "a", "infra/deploy/prod/main.tf": "b",
            "docker-compose.staging.yml": "c", "infra/compose/dev.yml": "d",
            ".github/workflows/deploy.yml": "jobs:\n  go:\n    environment: production\n"}
    d = detect(make_repo(tmp / "r", tree, manifest=None))
    assert list(d["environments"]) == ["dev", "staging", "prod", "production"], d["environments"]
    assert "infra/compose/dev.yml" in d["environments"]["dev"], d["environments"]


def test_detect_near_empty_and_untracked_files(tmp):
    d = detect(make_repo(tmp / "r", {"README.md": "x", "LICENSE": "x"}, manifest=None))
    assert d["near_empty"], d
    (tmp / "r/src").mkdir()
    (tmp / "r/src/new.py").write_text("x")  # untracked, not ignored: a new repo counts it
    assert not detect(tmp / "r")["near_empty"]


def test_no_manifest_prints_options(tmp):
    r = check(make_repo(tmp / "r", {"README.md": "x"}, manifest=None))
    assert r.returncode == 0, r.stdout
    for s in ("structure checking is off", "Detected mode: single", "monorepo", "multi-repo",
              "--bootstrap", "set up the repo structure"):
        assert s in r.stdout, (s, r.stdout)


def test_bootstrap_writes_a_manifest_that_passes(tmp):
    root = make_repo(tmp / "r", {"README.md": "x", "src/a.py": "x", "tools/b.sh": "x"}, manifest=None)
    r = check(root, "--bootstrap")
    assert r.returncode == 0 and "Wrote .claude/structure.toml" in r.stdout, r.stdout
    text = (root / ".claude/structure.toml").read_text()
    assert 'path = "src"' in text and 'path = "tools"' in text and "TODO" in text, text
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = check(root)
    assert r.returncode == 0, r.stdout


def test_bootstrap_never_overwrites(tmp):
    root = make_repo(tmp / "r", {"README.md": "x"})
    before = (root / ".claude/structure.toml").read_text()
    r = check(root, "--bootstrap")
    assert r.returncode == 2 and "already exists" in r.stdout, r.stdout
    assert (root / ".claude/structure.toml").read_text() == before


def test_bootstrap_mode_override_and_commented_suggestions(tmp):
    subprocess.run(["git", "init", "-q", str(tmp / "api")], check=True)
    root = make_repo(tmp / "r", {"README.md": "x", "infra/env/dev/.env.example": "a"}, manifest=None)
    assert check(root, "--bootstrap", "--mode", "multi-repo").returncode == 0
    text = (root / ".claude/structure.toml").read_text()
    assert 'mode = "multi-repo"' in text, text
    assert '# name = "api"' in text and '# path = "../api"' in text, text   # sibling pointer, commented
    assert '# name = "dev"' in text and '# target = "local"' in text, text   # seen env, commented


def test_bootstrap_warns_about_tracked_secrets_and_never_baselines_them(tmp):
    """A root .env is ALSO an unlisted root file; baselining that exact path would silence the
    secrets FAIL too (found adopting a real repo). Bootstrap must leave secrets failing."""
    root = make_repo(tmp / "r", {"README.md": "x", ".env": "S=1", "src/.env": "S=1", "notes.txt": "x"},
                     manifest=None)
    r = check(root, "--bootstrap", "--layout", "single")
    assert r.returncode == 0 and "FAIL  .env " in r.stdout and "FAIL  src/.env " in r.stdout, r.stdout
    text = (root / ".claude/structure.toml").read_text()
    assert '"notes.txt"' in text and '".env"' not in text, text
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = check(root)
    assert r.returncode == 1 and "FAIL  .env " in r.stdout and "FAIL  src/.env " in r.stdout, r.stdout


def test_bootstrap_unknown_layout_exits_2(tmp):
    r = check(make_repo(tmp / "r", {"README.md": "x"}, manifest=None), "--bootstrap", "--layout", "nope")
    assert r.returncode == 2 and "no layout 'nope'" in r.stdout, r.stdout


# ── layouts ──────────────────────────────────────────────────────────────────

LAYOUTS = REPO / ".claude/templates/structure"


def test_every_shipped_layout_is_a_valid_manifest(tmp):
    names = sorted(p.stem for p in LAYOUTS.glob("*.toml"))
    assert names == ["monorepo", "multi-repo", "single"], names
    for name in names:
        root = make_repo(tmp / name, {"README.md": "x"}, manifest=(LAYOUTS / f"{name}.toml").read_text())
        r = check(root)
        assert r.returncode in (0, 1), f"{name}: {r.stdout}"  # 2 would mean an invalid manifest
        assert f'mode: {name}' in r.stdout, r.stdout


def test_bootstrap_from_layout_adopts_an_existing_repo(tmp):
    tree = {"README.md": "x", "src/a.py": "x", "infra/env/dev/.env.example": "a",
            "legacy/old.py": "x", "notes.txt": "x", "infra/compose/notes.txt": "x"}
    root = make_repo(tmp / "r", tree, manifest=None)
    r = check(root, "--bootstrap", "--layout", "single")
    assert r.returncode == 0 and "layout: single" in r.stdout, r.stdout
    text = (root / ".claude/structure.toml").read_text()
    # folders that exist are active, the rest planned
    assert 'path = "src"\npurpose = "Application source"\nstatus = "active"' in text, text
    assert 'path = "migrations"' in text and 'status = "planned"' in text, text
    # the existing structure wins: an unknown top-level folder becomes its own entry...
    assert 'path = "legacy"\npurpose = "TODO: what belongs here (not in the single layout)"' in text, text
    # ...and the baseline is exact paths, never a glob that would allow future files
    assert 'exceptions = ["infra/compose/notes.txt", "notes.txt"]' in text, text
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = check(root)
    assert r.returncode == 0 and "allowed by exceptions" in r.stdout, r.stdout
    # ...and a NEW violation still blocks, including next to a baselined one
    (root / "stray.txt").write_text("x")
    (root / "infra/compose/todo.txt").write_text("x")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = check(root, "--staged")
    assert r.returncode == 1 and "FAIL  stray.txt" in r.stdout and "FAIL  infra/compose/todo.txt" in r.stdout, r.stdout


def test_bootstrap_from_layout_on_a_new_repo_plans_everything(tmp):
    root = make_repo(tmp / "r", {"README.md": "x"}, manifest=None)
    assert check(root, "--bootstrap", "--layout", "monorepo").returncode == 0
    text = (root / ".claude/structure.toml").read_text()
    assert 'status = "active"' not in text and "exceptions" not in text, text
    assert 'name = "stg"' in text and 'mirrors = "prod"' in text, text


# ── skill ────────────────────────────────────────────────────────────────────

def test_skill_only_names_flags_and_paths_that_exist():
    """The skill drives the script: a renamed flag or moved template breaks it silently."""
    skill = (REPO / "skills/structure-bootstrap/SKILL.md").read_text()
    assert skill.startswith("---\nname: structure-bootstrap\n"), skill[:60]
    helptext = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True).stdout
    git_flags = {"--no-verify", "--cached"}
    for flag in sorted(set(re.findall(r"(--[a-z][a-z-]+)", skill)) - git_flags):
        assert flag in helptext, f"skill names {flag}, script has no such flag"
    for path in (".claude/project-map/structure-check.py", ".claude/templates/structure"):
        assert path in skill and (REPO / path).exists(), path


# ── hook + installer ─────────────────────────────────────────────────────────

def _block(text: str) -> str:
    return text[text.index("# ── Structure Check"):text.index("# ── End Structure Check")]


def test_installer_writes_the_same_hook_block():
    assert _block((REPO / ".githooks/pre-commit").read_text()) == _block((REPO / ".claude/install.sh").read_text())


def test_install_copies_the_check_and_never_touches_the_manifest(tmp):
    root = make_repo(tmp / "p", {"README.md": "x"}, manifest='mode = "single"\n# hand-written\n', commit=False)
    before = (root / ".claude/structure.toml").read_bytes()
    for _ in range(2):  # re-running (init / update) must be just as safe
        r = subprocess.run(["bash", str(REPO / ".claude/install.sh"), str(root)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert (root / ".claude/structure.toml").read_bytes() == before
    assert (root / ".claude/project-map/structure-check.py").is_file()
    assert sorted(p.name for p in (root / ".claude/templates/structure").glob("*.toml")) == \
        ["monorepo.toml", "multi-repo.toml", "single.toml"]
    hook = (root / ".githooks/pre-commit").read_text()
    assert hook.count("# ── Structure Check") == 1, "re-running the installer duplicated the block"


def test_installer_checksum_matches_install_sh():
    """The curl installer verifies this hash first; editing install.sh without it breaks installs (runbook)."""
    import hashlib
    want = json.loads((REPO / "checksums.json").read_text())["install_sh"]
    assert hashlib.sha256((REPO / ".claude/install.sh").read_bytes()).hexdigest() == want, \
        "regenerate checksums.json: sha256sum .claude/install.sh"


def test_installer_upgrades_a_hook_from_before_the_structure_check(tmp):
    root = make_repo(tmp / "p", {"README.md": "x"}, manifest=None, commit=False)
    current = (REPO / ".githooks/pre-commit").read_text()
    old = current[:current.index("# ── Structure Check")].rstrip() + "\n"   # a 2.5.0-era hook
    assert "Context Check" in old and "Structure Check" not in old
    (root / ".githooks").mkdir()
    (root / ".githooks/pre-commit").write_text(old)
    r = subprocess.run(["bash", str(REPO / ".claude/install.sh"), str(root)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    hook = (root / ".githooks/pre-commit").read_text()
    assert hook.count("# ── Structure Check") == 1 and hook.count("# ── Context Check") == 1, hook


def test_submodules_are_paths_like_any_other(tmp):
    lib = make_repo(tmp / "lib", {"x.py": "x"}, manifest=None)
    root = make_repo(tmp / "r", {"README.md": "x"}, manifest=None)
    subprocess.run(GIT + ["-c", "protocol.file.allow=always", "submodule", "-q", "add", str(lib), "libs/vendor"],
                   cwd=root, check=True, capture_output=True)
    d = detect(root)
    assert d["submodules"] and any(".gitmodules" in r for r in d["reasons"]), d
    (root / ".claude").mkdir()
    (root / ".claude/structure.toml").write_text('root_files = ["README.md", ".gitmodules"]\n\n[[folder]]\npath = "libs"\n')
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = check(root)
    assert r.returncode == 0, r.stdout   # the gitlink is one path under libs/; its contents aren't ours
    (root / ".claude/structure.toml").write_text('root_files = ["README.md", ".gitmodules"]\n')
    r = check(root)
    assert r.returncode == 1 and "FAIL  libs/vendor " in r.stdout, r.stdout


def test_moving_a_file_into_a_deprecated_folder_counts_as_new(tmp):
    make_repo(tmp, {"README.md": "x", "src/a.py": "x", "legacy/old.py": "y"},
              manifest=DEPRECATED.replace('["**/*.py"]', '["**"]'))
    subprocess.run(["git", "checkout", "-qb", "feature"], cwd=tmp, check=True)
    subprocess.run(["git", "mv", "src/a.py", "legacy/a.py"], cwd=tmp, check=True)
    subprocess.run(GIT + ["commit", "-qm", "move"], cwd=tmp, check=True)
    r = check(tmp, "--since", "main")
    assert r.returncode == 1 and "legacy/a.py" in r.stdout and "legacy/old.py" not in r.stdout, r.stdout


def test_since_on_a_shallow_clone_explains_fetch_depth(tmp):
    origin = make_repo(tmp / "origin", {"README.md": "x", "src/a.py": "x"})
    subprocess.run(["git", "checkout", "-qb", "feature"], cwd=origin, check=True)
    for i in range(3):
        (origin / f"src/f{i}.py").write_text(str(i))
        subprocess.run(["git", "add", "-A"], cwd=origin, check=True)
        subprocess.run(GIT + ["commit", "-qm", f"c{i}"], cwd=origin, check=True)
    subprocess.run(["git", "checkout", "-q", "main"], cwd=origin, check=True)
    (origin / "src/m.py").write_text("main moved on")
    subprocess.run(["git", "add", "-A"], cwd=origin, check=True)
    subprocess.run(GIT + ["commit", "-qm", "main"], cwd=origin, check=True)
    ci = tmp / "ci"
    subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", "feature", f"file://{origin}", str(ci)], check=True)
    subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "main:refs/remotes/origin/main"], cwd=ci, check=True)
    r = check(ci, "--since", "origin/main")
    assert r.returncode == 2 and "fetch-depth: 0" in r.stdout, r.stdout


def test_hook_blocks_a_misplaced_file_only_once_there_is_a_manifest(tmp):
    root = make_repo(tmp / "p", {"README.md": "x"}, manifest=None)
    (root / ".githooks").mkdir()
    shutil.copy(REPO / ".githooks/pre-commit", root / ".githooks/pre-commit")
    (root / ".githooks/pre-commit").chmod(0o755)
    (root / ".claude/project-map").mkdir(parents=True)
    shutil.copy(SCRIPT, root / ".claude/project-map/structure-check.py")
    git = GIT + ["-c", "core.hooksPath=.githooks"]

    def commit(msg: str) -> subprocess.CompletedProcess:
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        return subprocess.run(git + ["commit", "-qm", msg], cwd=root, capture_output=True, text=True)

    (root / "stray.txt").write_text("x")
    assert commit("no manifest: check is off").returncode == 0

    (root / ".claude/structure.toml").write_text(
        'root_files = ["README.md", "stray.txt"]\n\n[[folder]]\npath = ".githooks"\n\n'
        '[[folder]]\npath = ".claude"\n')
    assert commit("manifest").returncode == 0

    (root / "tools").mkdir()
    (root / "tools/x.sh").write_text("x")
    r = commit("misplaced")
    assert r.returncode != 0, "hook let a file under no manifest folder through"
    out = r.stdout + r.stderr  # git hands a hook's stdout to stderr
    assert "[structure-check] Commit blocked" in out and "FAIL  tools/x.sh" in out, out


REALISTIC_MONOREPO = {
    "README.md": "x", "package.json": '{"workspaces": ["apps/*", "packages/*"]}', "pnpm-workspace.yaml": "p",
    "apps/api/package.json": '{"name": "api"}', "apps/api/src/index.ts": "api",
    "apps/api/migrations/001_init.sql": "create", "apps/api/src/seed/dev-users.ts": "seed code",
    "apps/web/package.json": '{"name": "web"}', "apps/web/src/pages/index.tsx": "web",
    "apps/web/src/features/prod-banner.tsx": "a component that merely mentions prod",
    "apps/web/config/environments/production.rb": "rails-style per-env FILE, not a folder",
    "packages/ui/package.json": '{"name": "ui"}', "packages/ui/src/button.tsx": "btn",
    "infra/compose/base.yml": "services: {api: {}}", "infra/compose/dev.yml": "dev override",
    "infra/compose/remote.yml": "remote override",
    "infra/env/dev/.env.example": "API_URL=http://localhost", "infra/env/stg/.env.example": "API_URL=https://stg",
    "infra/env/prod/.env.example": "API_URL=https://prod", "infra/env/README.md": "how env config works",
    "infra/deploy/base/main.tf": "module", "infra/deploy/base/variables.tf": "vars",
    "infra/deploy/stg/main.tf": 'module "app" { source = "../base" }',
    "infra/deploy/prod/main.tf": 'module "app" { source = "../base" }',  # identical ACROSS envs is fine
    "infra/deploy/stg/terraform.tfvars": "size = small", "infra/deploy/prod/terraform.tfvars": "size = large",
    "k8s/base/deployment.yaml": "deploy", "k8s/base/kustomization.yaml": "base",
    "k8s/overlays/stg/kustomization.yaml": "stg patch", "k8s/overlays/prod/kustomization.yaml": "prod patch",
    ".github/workflows/deploy.yml": "on: workflow_dispatch\njobs:\n  d:\n    environment: ${{ inputs.env }}\n",
    ".github/workflows/ci.yml": "ci",
}


def test_realistic_monorepo_with_environments_passes_clean(tmp):
    """False-positive guard: common, correct patterns must pass untouched."""
    m = (REPO / ".claude/templates/structure/monorepo.toml").read_text()
    m = m.replace('mode = "monorepo"', 'mode = "monorepo"\nenv_roots = ["infra/env", "infra/deploy", "k8s/overlays"]')
    m += '\n[[folder]]\npath = "k8s"\npurpose = "Kustomize base + per-env overlays"\n'
    r = check(make_repo(tmp / "r", REALISTIC_MONOREPO, manifest=m))
    assert r.returncode == 0 and "FAIL" not in r.stdout, r.stdout
    d = detect(tmp / "r")
    assert d["mode"] == "monorepo" and set(d["environments"]) >= {"dev", "stg", "prod"}, d


def test_realistic_monorepo_catches_the_classic_drift(tmp):
    m = (REPO / ".claude/templates/structure/monorepo.toml").read_text()
    m = m.replace('mode = "monorepo"', 'mode = "monorepo"\nenv_roots = ["infra/env", "infra/deploy", "k8s/overlays"]')
    m += '\n[[folder]]\npath = "k8s"\npurpose = "Kustomize base + per-env overlays"\n'
    drift = {
        "apps/api/config/prod/.env.example": "per-app env config",        # per-app config/<env>/
        "apps/api/env/prod/.env.example": "per-app env folder",            # per-app env folder
        "infra/deploy/prod/redis.tf": "redis only in prod",                 # stg no longer mirrors prod
        "infra/deploy/prod/variables.tf": "vars",                           # copy of base/variables.tf
        "infra/env/qa/.env.example": "QA=1",                                # undeclared environment
        "apps/api/migrations/prod/002_hotfix.sql": "prod-only migration",   # per-env migration
        "docker-compose.yml": "compose at the root",                        # compose outside infra/compose
    }
    r = check(make_repo(tmp / "r", {**REALISTIC_MONOREPO, **drift}, manifest=m))
    assert r.returncode == 1, r.stdout
    for needle in ("apps/api/config/prod/", "apps/api/env/prod/", "infra/deploy/stg/redis.tf", "identical copy of infra/deploy/base/variables.tf",
                   "infra/env/qa/", "apps/api/migrations/prod/002_hotfix.sql", "FAIL  docker-compose.yml"):
        assert needle in r.stdout, (needle, r.stdout)


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
