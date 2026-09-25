#!/bin/bash
# ============================================================
# Babel Fish Plugin — Installer
# Triggered automatically on plugin installation.
#
# What this does:
#   1. Checks / installs Python >= 3.8
#   2. Detects project stack
#   3. Runs generate.py → grades with grader.py (up to 3 iterations)
#   4. Renders skill + rules files from templates
#   5. Installs git hooks
#   6. Prints a final summary with the grade report path
#
# Usage:
#   bash .claude/install.sh [project-root]
# ============================================================

set -euo pipefail

# ── Help ──────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<'HELP'

  ╔══════════════════════════════════════════════════════════════════╗
  ║              Babel Fish Plugin — Help                       ║
  ╚══════════════════════════════════════════════════════════════════╝

WHAT IT DOES
  Builds a self-updating developer context system for your repo:
  - Project map split into 19 focused sections (routes, models, infra, etc.)
  - Vocabulary translator: maps plain English to exact file paths
  - Developer skill auto-loaded in every Claude Code session
  - Operational runbook for gotchas and deploy procedures
  - Pre-commit hook that keeps the map current automatically
  - Iterative quality grading (0-100%) with a 90% pass threshold

REQUIREMENTS
  - Claude Code >= 1.0.0
  - Python >= 3.8  (auto-installed if missing)
  - bash
  - Optional: pip install pyyaml  (for docker-compose parsing)

INSTALLATION
  Preview all changes first (nothing is modified):

    bash .claude/install.sh --dry-run

  Run the installer:

    bash .claude/install.sh

  Or with an explicit project root:

    bash .claude/install.sh /path/to/your/project

  One-liner from the internet (checksum-verified):

    curl -sSL https://raw.githubusercontent.com/TheGlitchKing/babel-fish/main/install.sh | bash

  Preview before running remotely:

    curl -sSL https://raw.githubusercontent.com/TheGlitchKing/babel-fish/main/install.sh | bash -s -- --dry-run

  Via npm (no curl needed):

    npx @theglitchking/babel-fish dry-run
    npx @theglitchking/babel-fish init

  Via the Glitch Kingdom Marketplace in Claude Code:

    /plugin marketplace add TheGlitchKing/glitch-kingdom-of-plugins
    /plugin install TheGlitchKing/babel-fish

WHAT HAPPENS ON INSTALL
  1. Python >= 3.8 is checked and installed if missing
  2. Stack is detected (language, framework, DB, ORM, auth, infra)
  3. generate.py runs to build the 19-section project map
  4. grader.py scores the output 0-100% across 7 categories
  5. If score < 90%, it retries up to 3 times automatically
  6. Skills and rules files are rendered from templates
  7. Pre-commit git hook is installed
  8. CLAUDE.md is updated with a project map pointer
  9. A final quality report is written to:
       .claude/project-map/reports/install-report.md

POST-INSTALL COMMANDS
  Regenerate the map (forced):
    python .claude/project-map/generate.py --force

  Regenerate only if files changed (fast, used by pre-commit):
    python .claude/project-map/generate.py

  Re-grade the current map output:
    python .claude/project-map/grader.py

  Mine past Claude Code sessions for vocabulary aliases:
    python .claude/project-map/mine-sessions.py
    python .claude/project-map/mine-sessions.py --verbose
    python .claude/project-map/mine-sessions.py --dry-run

  Check auto-loaded context (CLAUDE.md + .claude/rules/) — budget, pointers:
    python .claude/project-map/context-check.py
    python .claude/project-map/context-check.py --budget 80000 --map-style

  Re-install git hooks (if you cloned a fresh copy):
    bash .githooks/install.sh

  Re-run the full installer:
    bash .claude/install.sh

USING THE DEVELOPER SKILL
  After install, invoke your project skill in Claude Code:

    /babel-fish-developer    (or /<your-project-slug>-developer)

  The skill reads PROJECT_MAP.md and loads only the 2-3 sections
  relevant to your current task (typically 5-20KB of context).

KEY FILES AFTER INSTALL
  .claude/project-map/PROJECT_MAP.md        — Map index + quick routing
  .claude/project-map/sections/01-*.md      — Vocabulary translator
  .claude/project-map/sections/04-*.md      — API routes
  .claude/project-map/sections/05-*.md      — Data models
  .claude/project-map/reports/install-report.md — Quality report
  .claude/rules/project-vocabulary.md       — Auto-loaded every session
  .claude/rules/operational-runbook.md      — Edit manually to grow over time
  .claude/skills/<slug>-developer-skill/    — Your developer skill
  .githooks/pre-commit                      — Regenerates map; checks auto-loaded context

GRADING CATEGORIES (90% to pass)
  Section completeness  25%  — All 19 sections generated
  Vocabulary accuracy   20%  — Entries map to real files
  Import chain validity 15%  — Chains trace to real modules
  Secret safety         15%  — No API keys or tokens leaked
  Section size bounds   10%  — Each section 0.1-50KB
  Structural integrity  10%  — Valid markdown, working TOC links
  Checksum function      5%  — Re-run skips when nothing changed

EXAMPLES
  # Install on current directory
  bash .claude/install.sh

  # Install on a specific project
  bash .claude/install.sh /mnt/e/my-project

  # Force-regenerate after adding new routes
  python .claude/project-map/generate.py --force

  # Check map quality after a big refactor
  python .claude/project-map/grader.py

  # See what vocabulary aliases were learned from your sessions
  python .claude/project-map/mine-sessions.py --dry-run --verbose

HELP

    exit 0
fi

# ── Argument parsing ─────────────────────────────────────────────────────────
DRY_RUN=false
POSITIONAL=""
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        -*) ;;  # ignore unknown flags
        *) POSITIONAL="$arg" ;;
    esac
done

# Resolve absolute path immediately
PROJECT_ROOT="$(cd "${POSITIONAL:-$(pwd)}" && pwd)"
PLUGIN_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"
MAP_DIR="$CLAUDE_DIR/project-map"
REPORTS_DIR="$MAP_DIR/reports"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
TEMPLATES_DIR="$CLAUDE_DIR/templates"

MAX_ITERATIONS=3
PASS_THRESHOLD=90
PREVIOUS_SCORE=""

# Dry-run helper — prints the action instead of doing it
_dry() { printf '%b\n' "${YELLOW}  [dry-run] $*${RESET}"; }

# ── Colors ───────────────────────────────────────────────────────────────────
CYAN='\033[36m'; GREEN='\033[32m'; YELLOW='\033[33m'; RED='\033[31m'
BOLD='\033[1m'; RESET='\033[0m'

banner() { printf '\n%b\n' "${CYAN}${BOLD}══ $* ══${RESET}"; }
step()   { printf '%b\n' "${CYAN}▶ $*${RESET}"; }
ok()     { printf '%b\n' "${GREEN}✓ $*${RESET}"; }
warn()   { printf '%b\n' "${YELLOW}⚠ $*${RESET}"; }
fail()   { printf '%b\n' "${RED}✗ $*${RESET}"; }
info()   { printf '%b\n' "  $*"; }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  HELPER FUNCTIONS  (must be defined before main flow)                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

_improve_for_next_iteration() {
    local score_json="$1"
    local python_cmd="$3"

    [ -f "$score_json" ] || return

    local issues
    issues=$("$python_cmd" -c "
import json
d = json.load(open('$score_json'))
for issue in d.get('issues', []):
    print(issue['category'] + ': ' + issue['issue'])
" 2>/dev/null || true)

    if [ -n "$issues" ]; then
        info "Issues from previous iteration:"
        echo "$issues" | while IFS= read -r line; do
            info "  → $line"
        done
    fi
    info "Will re-run generate.py with --force for next iteration..."
}

_render_vocabulary() {
    local project_root="$1"
    local name="$2"
    local lang="$3"
    local framework="$4"
    local rules_dir="$5"
    local out="$rules_dir/project-vocabulary.md"
    local template="$TEMPLATES_DIR/project-vocabulary.md.template"

    if [ -f "$template" ]; then
        sed \
            -e "s|{{PROJECT_NAME}}|$name|g" \
            -e "s|{{LANGUAGE}}|$lang|g" \
            -e "s|{{FRAMEWORK}}|$framework|g" \
            "$template" > "$out"
    else
        cat > "$out" <<VOCAB
# ${name} — Project Vocabulary

> Auto-loaded every session. Maps human language to exact code locations.

## Feature → Code Location

| You Say | Frontend | Backend | Model/Table |
|---------|----------|---------|-------------|
| _(vocabulary populates as source code is added)_ | | | |

## Quick Actions

| You Say | What To Do |
|---------|-----------|
| regenerate map | \`python .claude/project-map/generate.py --force\` |
| grade map | \`python .claude/project-map/grader.py\` |
VOCAB
    fi
    ok "Rendered: $out"
}

_render_runbook() {
    local name="$2"
    local rules_dir="$3"
    local out="$rules_dir/operational-runbook.md"
    local template="$TEMPLATES_DIR/operational-runbook.md.template"

    if [ -f "$out" ]; then
        ok "Runbook already exists — preserving: $out"
        return
    fi

    if [ -f "$template" ]; then
        sed -e "s|{{PROJECT_NAME}}|$name|g" "$template" > "$out"
    else
        cat > "$out" <<RUNBOOK
# ${name} — Operational Runbook

> Auto-loaded every session. Edit this file manually — NOT overwritten on regeneration.

## Environment Differences

| | Dev | Staging | Production |
|---|---|---|---|
| **URL** | | | |
| **Database** | | | |

## Known Issues & Workarounds

_No known issues documented yet._

## Key Commands

| Command | What It Does |
|---------|-------------|
| \`python .claude/project-map/generate.py --force\` | Regenerate project map |
| \`python .claude/project-map/grader.py\` | Grade map quality |
RUNBOOK
    fi
    ok "Rendered: $out"
}

_render_skill() {
    local project_root="$1"
    local name="$2"
    local slug="$3"
    local lang="$4"
    local framework="$5"
    local skills_dir="$6"
    local out="$skills_dir/SKILL.md"
    local template="$TEMPLATES_DIR/SKILL.md.template"

    if [ -f "$template" ]; then
        sed \
            -e "s|{{PROJECT_NAME}}|$name|g" \
            -e "s|{{PROJECT_SLUG}}|$slug|g" \
            -e "s|{{LANGUAGE}}|$lang|g" \
            -e "s|{{FRAMEWORK}}|$framework|g" \
            "$template" > "$out"
    else
        cat > "$out" <<SKILL
---
name: ${slug}-developer-skill
description: |
  Full-stack developer context for ${name} (${lang}/${framework}).
  Invoke when working on any ${name} feature, bug, or infrastructure task.
---

# /${slug}-developer — ${name} Developer Context

## On Trigger

\`\`\`
Read: .claude/project-map/PROJECT_MAP.md
\`\`\`

Use the Quick Routing table to pick 2-3 sections to load.

## Section Routing

| Task | Read These Sections |
|------|-------------------|
| Feature / UX work | 01-vocabulary → 09-frontend → 04-routes |
| Add a model or field | 05-models → 06-schemas → 12-import-chains |
| Troubleshoot error | 02-topology → 03-environment → 14-proxy |
| Infrastructure | 16-infra-profile → 02-topology |
| Auth / security | 15-auth-config |
| Tools | 10-tools-commands |

## Stack: ${lang} / ${framework}
SKILL
    fi
    ok "Rendered: $out"
}

_install_git_hooks() {
    local project_root="$1"
    local hooks_dir="$2"
    local pre_commit="$hooks_dir/pre-commit"

    local hook_snippet='# ── Codebase Mapper: regenerate project map on relevant changes ──
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || true)
EXTENSIONS_PATTERN='"'"'\.(py|ts|tsx|js|jsx|go|java|yaml|yml)$|docker-compose|package\.json|Cargo\.toml|go\.mod'"'"'
if echo "$STAGED_FILES" | grep -qE "$EXTENSIONS_PATTERN" 2>/dev/null; then
    MAP_SCRIPT=".claude/project-map/generate.py"
    if [ -f "$MAP_SCRIPT" ]; then
        PYTHON=""
        if [ -f ".venv/bin/python3" ]; then PYTHON=".venv/bin/python3"
        elif command -v python3 &>/dev/null; then PYTHON="python3"
        elif command -v python &>/dev/null; then PYTHON="python"
        fi
        if [ -n "$PYTHON" ]; then
            echo "[codebase-mapper] Regenerating project map..."
            if $PYTHON "$MAP_SCRIPT" 2>/dev/null; then
                git add .claude/project-map/PROJECT_MAP.md .claude/project-map/checksums.json \
                        .claude/project-map/sections/*.md .claude/project-map/learned-vocabulary.json 2>/dev/null || true
            fi
        fi
    fi
fi
# ── End Codebase Mapper ──────────────────────────────────────────────────────'

    # Own marker, checked separately: hooks installed before #20 already carry
    # the Codebase Mapper block, and re-running the installer must still add this.
    local check_snippet
    check_snippet=$(cat <<'SNIPPET'
# ── Context Check: auto-loaded instructions stay in budget, pointers resolve ──
if git diff --cached --name-only 2>/dev/null | grep -qE '^(\.claude/)?CLAUDE(\.local)?\.md$|^\.claude/rules/.*\.md$'; then
    CHECK_SCRIPT=".claude/project-map/context-check.py"
    if [ -f "$CHECK_SCRIPT" ]; then
        PYTHON=""
        if [ -f ".venv/bin/python3" ]; then PYTHON=".venv/bin/python3"
        elif command -v python3 &>/dev/null; then PYTHON="python3"
        elif command -v python &>/dev/null; then PYTHON="python"
        fi
        if [ -n "$PYTHON" ] && ! $PYTHON "$CHECK_SCRIPT"; then
            echo "[context-check] Commit blocked. Fix the FAIL lines above, or add flags (--budget N, --map-style) to this call in .githooks/pre-commit." >&2
            exit 1
        fi
    fi
fi
# ── End Context Check ────────────────────────────────────────────────────────
SNIPPET
)

    if [ ! -f "$pre_commit" ]; then
        printf '#!/bin/bash\n' > "$pre_commit"
        ok "Created pre-commit hook"
    fi
    if ! grep -q 'Codebase Mapper' "$pre_commit" 2>/dev/null; then
        { echo ""; echo "$hook_snippet"; } >> "$pre_commit"
        ok "Added Codebase Mapper to pre-commit hook"
    else
        ok "pre-commit hook already contains Codebase Mapper snippet"
    fi
    if ! grep -q 'Context Check' "$pre_commit" 2>/dev/null; then
        { echo ""; echo "$check_snippet"; } >> "$pre_commit"
        ok "Added Context Check to pre-commit hook"
    else
        ok "pre-commit hook already contains Context Check snippet"
    fi

    chmod +x "$pre_commit"

    cat > "$hooks_dir/install.sh" <<'INSTALL'
#!/bin/bash
git config core.hooksPath .githooks
chmod +x .githooks/*
echo "Git hooks installed (.githooks/ directory configured)"
INSTALL
    chmod +x "$hooks_dir/install.sh"

    if git -C "$project_root" rev-parse --git-dir > /dev/null 2>&1; then
        git -C "$project_root" config core.hooksPath .githooks
        ok "Configured git to use .githooks/"
    fi
}

_update_claude_md() {
    local project_root="$1"
    local name="$2"
    local claude_md="$project_root/.claude/CLAUDE.md"

    if [ -f "$claude_md" ] && grep -q 'Project Map' "$claude_md" 2>/dev/null; then
        ok "CLAUDE.md already has Project Map section"
        return
    fi

    local pointer
    pointer=$(cat <<'POINTER'

## Project Map

**Project Map**: For any project-specific question, read
[`.claude/project-map/PROJECT_MAP.md`](.claude/project-map/PROJECT_MAP.md) —
auto-generated index of routes, models, import chains, infra profile,
and vocabulary translator. Regenerated automatically on commit.

To regenerate manually:
```bash
python .claude/project-map/generate.py --force
```
POINTER
)

    if [ -f "$claude_md" ]; then
        echo "$pointer" >> "$claude_md"
        ok "Updated CLAUDE.md with Project Map pointer"
    else
        cat > "$claude_md" <<CLAUDEMD
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**${name}** — see README.md for details.
${pointer}
CLAUDEMD
        ok "Created CLAUDE.md"
    fi
}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  MAIN FLOW                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

printf '%b\n' "
${CYAN}${BOLD}
  ╔══════════════════════════════════════════╗
  ║     Babel Fish Plugin Installer     ║
  ║     by TheGlitchKing                     ║
  ╚══════════════════════════════════════════╝
${RESET}"

info "Project root: $PROJECT_ROOT"
info "Timestamp:    $(date '+%Y-%m-%d %H:%M:%S')"
echo

# ── Dry-run preview ──────────────────────────────────────────────────────────
if $DRY_RUN; then
    printf '%b\n' "${YELLOW}${BOLD}  DRY RUN — nothing will be created or modified${RESET}"
    echo
    printf '%b\n' "${CYAN}${BOLD}  Files this installer will create:${RESET}"
    _dry "mkdir -p $CLAUDE_DIR/scripts"
    _dry "mkdir -p $CLAUDE_DIR/templates"
    _dry "mkdir -p $CLAUDE_DIR/project-map/sections"
    _dry "mkdir -p $CLAUDE_DIR/project-map/reports"
    _dry "mkdir -p $CLAUDE_DIR/rules"
    _dry "mkdir -p $CLAUDE_DIR/skills/<project>-developer-skill/"
    _dry "copy  scripts/*.sh         → $CLAUDE_DIR/scripts/"
    _dry "copy  templates/*.template → $CLAUDE_DIR/templates/"
    _dry "copy  project-map/*.py     → $CLAUDE_DIR/project-map/"
    _dry "write $CLAUDE_DIR/project-map/PROJECT_MAP.md"
    _dry "write $CLAUDE_DIR/project-map/sections/01-vocabulary.md  (+ 18 more sections)"
    _dry "write $CLAUDE_DIR/project-map/reports/install-report.md"
    _dry "write $CLAUDE_DIR/rules/project-vocabulary.md"
    _dry "write $CLAUDE_DIR/rules/operational-runbook.md"
    _dry "write $CLAUDE_DIR/skills/<project>-developer-skill/SKILL.md"
    _dry "write .githooks/pre-commit"
    _dry "run   git config core.hooksPath .githooks"
    _dry "write/update CLAUDE.md  (appends project map pointer)"
    echo
    printf '%b\n' "${CYAN}${BOLD}  What the installer will NOT do:${RESET}"
    _dry "  — will not modify any of your source files"
    _dry "  — will not install packages globally"
    _dry "  — will not make network requests (except git clone if run via curl)"
    _dry "  — will not run Python with elevated permissions"
    echo
    printf '%b\n' "${GREEN}  Run without --dry-run to apply.${RESET}"
    exit 0
fi

# ── Step 0: Bootstrap plugin files into target project ───────────────────────
# When running from an external source (e.g. marketplace install), copy all
# plugin scripts, templates, and python files into the target project's .claude/
if [ "$PLUGIN_SOURCE_DIR" != "$CLAUDE_DIR" ]; then
    mkdir -p "$CLAUDE_DIR/scripts" "$CLAUDE_DIR/templates" "$CLAUDE_DIR/project-map" "$CLAUDE_DIR/rules" "$CLAUDE_DIR/skills"
    cp -r "$PLUGIN_SOURCE_DIR/scripts/." "$CLAUDE_DIR/scripts/"
    cp -r "$PLUGIN_SOURCE_DIR/templates/." "$CLAUDE_DIR/templates/"
    cp -r "$PLUGIN_SOURCE_DIR/project-map/generate.py" "$CLAUDE_DIR/project-map/" 2>/dev/null || true
    cp -r "$PLUGIN_SOURCE_DIR/project-map/grader.py" "$CLAUDE_DIR/project-map/" 2>/dev/null || true
    cp -r "$PLUGIN_SOURCE_DIR/project-map/mine-sessions.py" "$CLAUDE_DIR/project-map/" 2>/dev/null || true
    cp -r "$PLUGIN_SOURCE_DIR/project-map/context-check.py" "$CLAUDE_DIR/project-map/" 2>/dev/null || true
fi

# ── Step 1: Ensure Python ─────────────────────────────────────────────────────
banner "Step 1: Python"

if [ ! -f "$SCRIPTS_DIR/ensure-python.sh" ]; then
    fail "ensure-python.sh not found at $SCRIPTS_DIR/ensure-python.sh"
    exit 2
fi

PYTHON_CMD=$(bash "$SCRIPTS_DIR/ensure-python.sh")
if [ -z "$PYTHON_CMD" ]; then
    fail "Could not find or install Python >= 3.8"
    exit 2
fi

ok "Python: $("$PYTHON_CMD" --version 2>&1)"

# ── Step 2: Detect Stack ──────────────────────────────────────────────────────
banner "Step 2: Stack Detection"

STACK_JSON="$MAP_DIR/stack.json"
mkdir -p "$MAP_DIR" "$REPORTS_DIR"

if [ -f "$SCRIPTS_DIR/detect-stack.sh" ]; then
    bash "$SCRIPTS_DIR/detect-stack.sh" "$PROJECT_ROOT" > "$STACK_JSON" 2>/dev/null || true
fi

if [ -f "$STACK_JSON" ] && "$PYTHON_CMD" -c "import json; json.load(open('$STACK_JSON'))" 2>/dev/null; then
    LANG=$("$PYTHON_CMD"   -c "import json; d=json.load(open('$STACK_JSON')); print(d.get('language','unknown'))")
    FRAMEWORK=$("$PYTHON_CMD" -c "import json; d=json.load(open('$STACK_JSON')); print(d.get('framework','unknown'))")
    NAME=$("$PYTHON_CMD"   -c "import json; d=json.load(open('$STACK_JSON')); print(d.get('name','project'))")
    SLUG=$("$PYTHON_CMD"   -c "import json; d=json.load(open('$STACK_JSON')); print(d.get('slug','project'))")
    ok "Detected: $NAME ($LANG / $FRAMEWORK)"
else
    warn "Stack detection unavailable — using directory name as defaults"
    NAME=$(basename "$PROJECT_ROOT")
    SLUG=$(echo "$NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g;s/^-//;s/-$//')
    LANG="unknown"
    FRAMEWORK="unknown"
fi

# ── Step 3: Iterative Generation + Grading ────────────────────────────────────
banner "Step 3: Generate → Grade (up to $MAX_ITERATIONS iterations)"

FINAL_SCORE=0
FINAL_PASSED=false

for ITERATION in $(seq 1 $MAX_ITERATIONS); do
    echo
    step "Iteration $ITERATION / $MAX_ITERATIONS"
    echo

    step "Running generate.py..."
    set +e
    "$PYTHON_CMD" "$MAP_DIR/generate.py" --force \
        --project-root "$PROJECT_ROOT" \
        --stack-json "$STACK_JSON"
    GEN_EXIT=$?
    set -e
    [ $GEN_EXIT -ne 0 ] && warn "generate.py exited with errors (continuing to grade what was produced)"

    step "Running grader.py..."
    GRADE_ARGS=(--iteration "$ITERATION" --total "$MAX_ITERATIONS" --project-root "$PROJECT_ROOT")
    [ -n "$PREVIOUS_SCORE" ] && GRADE_ARGS+=(--previous-score "$PREVIOUS_SCORE")

    set +e
    "$PYTHON_CMD" "$MAP_DIR/grader.py" "${GRADE_ARGS[@]}"
    GRADE_EXIT=$?
    set -e

    SCORE_JSON="$REPORTS_DIR/iteration-$(printf '%02d' "$ITERATION")-score.json"
    if [ -f "$SCORE_JSON" ]; then
        FINAL_SCORE=$("$PYTHON_CMD" -c "import json; print(json.load(open('$SCORE_JSON'))['score'])")
        PASSED=$("$PYTHON_CMD"      -c "import json; print(json.load(open('$SCORE_JSON'))['passed'])")
    else
        FINAL_SCORE=0
        PASSED="False"
    fi

    PREVIOUS_SCORE="$FINAL_SCORE"

    if [ "$PASSED" = "True" ]; then
        FINAL_PASSED=true
        ok "Score: ${FINAL_SCORE}% — PASSED ✓ (>= ${PASS_THRESHOLD}%)"
        break
    else
        warn "Score: ${FINAL_SCORE}% — below ${PASS_THRESHOLD}% threshold"
        if [ "$ITERATION" -lt "$MAX_ITERATIONS" ]; then
            step "Attempting improvements for iteration $((ITERATION + 1))..."
            _improve_for_next_iteration "$SCORE_JSON" "$MAP_DIR" "$PYTHON_CMD"
        fi
    fi
done

# ── Step 4: Render Templates ──────────────────────────────────────────────────
banner "Step 4: Render Skills & Rules"

RULES_DIR="$CLAUDE_DIR/rules"
SKILLS_DIR="$CLAUDE_DIR/skills/${SLUG}-developer-skill"
mkdir -p "$RULES_DIR" "$SKILLS_DIR"

_render_vocabulary "$PROJECT_ROOT" "$NAME" "$LANG" "$FRAMEWORK" "$RULES_DIR"
_render_runbook    "$PROJECT_ROOT" "$NAME" "$RULES_DIR"
_render_skill      "$PROJECT_ROOT" "$NAME" "$SLUG" "$LANG" "$FRAMEWORK" "$SKILLS_DIR"

# ── Step 5: Git Hooks ─────────────────────────────────────────────────────────
banner "Step 5: Git Hooks"

HOOKS_DIR="$PROJECT_ROOT/.githooks"
mkdir -p "$HOOKS_DIR"
_install_git_hooks "$PROJECT_ROOT" "$HOOKS_DIR"

# ── Step 6: Update CLAUDE.md ──────────────────────────────────────────────────
banner "Step 6: Update CLAUDE.md"
_update_claude_md "$PROJECT_ROOT" "$NAME"

# ── Step 7: Final Validation ──────────────────────────────────────────────────
banner "Step 7: Validation"

if [ -f "$SCRIPTS_DIR/validate.sh" ]; then
    bash "$SCRIPTS_DIR/validate.sh" "$PROJECT_ROOT" || true
else
    warn "validate.sh not found — skipping"
fi

# ── Summary ────���──────────────────────────────────────────────────────────────
echo
printf '%b\n' "${CYAN}${BOLD}══════════════════════════════════════════════════${RESET}"
printf '%b\n' "${BOLD}  Installation Complete${RESET}"
printf '%b\n' "${CYAN}══════════════════════════════════════════════════${RESET}"
echo

if [ "$FINAL_PASSED" = "true" ]; then
    printf '%b\n' "  ${GREEN}${BOLD}✓ PASSED${RESET} — Score: ${GREEN}${FINAL_SCORE}%${RESET}"
else
    printf '%b\n' "  ${YELLOW}${BOLD}⚠ COMPLETED WITH WARNINGS${RESET} — Score: ${YELLOW}${FINAL_SCORE}%${RESET}"
    info "Map generated but scored below 90%. Review report for details."
fi

echo
info "Project Map:     .claude/project-map/PROJECT_MAP.md"
info "Install Report:  .claude/project-map/reports/install-report.md"
info "Developer Skill: /${SLUG}-developer-skill"
echo
info "To regenerate:"
info "  $PYTHON_CMD .claude/project-map/generate.py --force"
info "  $PYTHON_CMD .claude/project-map/grader.py"
echo
printf '%b\n' "${CYAN}══════════════════════════════════════════════════${RESET}"
echo
