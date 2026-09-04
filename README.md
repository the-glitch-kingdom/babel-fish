# babel-fish

![babel-fish](babel.jpg)

**Gives your AI coding assistant instant, accurate knowledge of every route, model, service, feature, and infrastructure element in your codebase.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-green.svg)]()
[![GitHub: TheGlitchKing/babel-fish](https://img.shields.io/badge/GitHub-TheGlitchKing%2Fbabel--fish-blue)](https://github.com/TheGlitchKing/babel-fish)

> [!NOTE]
> **Pairs with [`semantic-memory`](https://github.com/TheGlitchKing/semantic-sidekick) (formerly `semantic-sidekick`).** When both are installed, semantic-memory consumes babel-fish's auto-generated `.babel-fish/` output as a `project-map` corpus AND extracts `01-vocabulary.md` into a structured `glossary.json` side-channel. That gives your AI a deterministic `translate("deals page") → "features/deal-pipeline/DealPipeline.tsx"` MCP verb instead of relying on semantic-search-luck. See [`.documentation/api/glossary-contract.md`](./.documentation/api/glossary-contract.md) for the producer/consumer data contract and [`.documentation/quickstart/integration-with-semantic-memory.md`](./.documentation/quickstart/integration-with-semantic-memory.md) for the setup walkthrough. babel-fish standalone behavior is unchanged — semantic-memory is purely additive.

---

## What Does This Do?

Babel Fish creates a translation layer between a human and an LLM. It provides a natural feature-based conversation for the human, and a direct mapping to tools, targets, models, and file paths for the AI. Babel Fish auto-generates a living project map for your codebase and teaches your AI assistant your vocabulary — so you spend zero time re-explaining your project every session.

| Without Babel Fish | With Babel Fish |
|-------------------|-----------------|
| "The deals page is at `features/deal-pipeline/DealPipeline.tsx`" | *Already mapped* |
| AI scans 200 files to find a route | *Loads 1 section, 5KB* |
| Stale context after a refactor | *Pre-commit hook auto-regenerates* |
| Re-explain your stack every session | *Vocabulary auto-loaded on start* |
| "Where is the background job for invoices?" | *Checks section 08 directly* |

**In short:** Your AI assistant knows your codebase cold from the first message.

---

## What Gets Generated

A 19-section project map, split into focused files so the AI loads only what's relevant per task:

| Section | What It Contains |
|---------|-----------------|
| `01-vocabulary.md` | Plain-English → exact file path mapping |
| `02-service-topology.md` | How your services connect |
| `03-environment.md` | Env vars (secrets redacted) |
| `04-api-routes.md` | Every route with method, path, handler |
| `05-data-models.md` | Models and their fields |
| `06-schemas.md` | Validation schemas (Pydantic, Zod, etc.) |
| `07-services.md` | Business logic layer |
| `08-background-jobs.md` | Queues, workers, cron tasks |
| `09-frontend-features.md` | Components and pages |
| `10-tools-commands.md` | CLI commands and scripts |
| `11-migrations.md` | Database migration history |
| `12-import-chains.md` | Key import dependency trees |
| `13-frontend-backend-map.md` | Which frontend calls which API |
| `14-reverse-proxy.md` | Nginx/Caddy routing config |
| `15-auth-config.md` | Auth strategy and guards |
| `16-infra-profile.md` | Docker, Terraform, cloud config |
| `17-learned-vocabulary.md` | Aliases mined from your sessions |
| `18-dead-code.md` | Unused exports and orphaned files |
| `19-doc-pointers.md` | Links to external docs |

Plus:
- **`PROJECT_MAP.md`** — TOC and quick routing guide (always loaded first)
- **`project-vocabulary.md`** — auto-loaded every session
- **`operational-runbook.md`** — gotchas and deploy procedures, grows over time
- **Developer skill** — loads only the 2-3 sections relevant to your current task

---

## Install

### Option 1: npx (recommended — no curl, verified by npm registry)

```bash
# Preview all changes before applying (nothing is modified)
npx @theglitchking/babel-fish dry-run

# Install
npx @theglitchking/babel-fish init

# Or target a specific project
npx @theglitchking/babel-fish init /path/to/your/project
```

---

### Option 2: Curl one-liner (checksum-verified)

Always preview before running anything from the internet:

```bash
# Preview first — shows every file that will be created, nothing is modified
curl -sSL https://raw.githubusercontent.com/TheGlitchKing/babel-fish/main/install.sh | bash -s -- --dry-run

# Install
curl -sSL https://raw.githubusercontent.com/TheGlitchKing/babel-fish/main/install.sh | bash

# Or target a specific path
curl -sSL https://raw.githubusercontent.com/TheGlitchKing/babel-fish/main/install.sh | bash -s -- /path/to/your/project
```

The remote installer verifies a SHA256 checksum against `checksums.json` before executing anything. If the file has been tampered with in transit, the installer aborts.

---

### Option 3: Via Glitch Kingdom Marketplace (Claude Code)

Run these inside a Claude Code session:

```
/plugin marketplace add TheGlitchKing/glitch-kingdom-of-plugins
/plugin install TheGlitchKing/babel-fish
```

> The first command registers the Glitch Kingdom marketplace. You only need to run it once — after that, `/plugin install` works for all Glitch Kingdom plugins.

---

### Option 4: Clone and run

```bash
git clone https://github.com/TheGlitchKing/babel-fish.git
bash babel-fish/.claude/install.sh --dry-run /path/to/your/project  # preview first
bash babel-fish/.claude/install.sh /path/to/your/project
```

---

## Update management *(2.0.0+)*

Every install ships with an update policy controlling what happens at session start when a newer version is available on npm. Default is `nudge` (one-liner notification, no automatic changes).

```bash
babel-fish status          # installed / latest / policy / hook state
babel-fish policy auto     # auto-update on session start
babel-fish policy nudge    # one-liner nudge only (default)
babel-fish policy off      # silent
babel-fish update          # update now
```

Slash-command parity: `/babel-fish:status`, `/babel-fish:policy <mode>`, `/babel-fish:update`, `/babel-fish:relink`.

See [CHANGELOG.md](./CHANGELOG.md) for the full 2.0.0 release notes, breaking-change details, and env-var opt-outs.

---

## What the Installer Does

1. Checks for Python ≥ 3.8 (installs if missing)
2. Detects your stack (language, framework, database, ORM, auth, infra)
3. Runs `generate.py` → grades with `grader.py` (iterates up to 3× until 90%+ quality)
4. Renders your developer skill and rules files
5. Installs the pre-commit hook (auto-regenerates map on source file changes)
6. Updates `CLAUDE.md` with a project map pointer
7. Prints a full quality report

---

## Quality Grading

Every install is graded 0–100% across 7 categories. Must score ≥ 90% to pass (up to 3 iterations):

| Category | Weight | What It Checks |
|----------|--------|----------------|
| Section completeness | 25% | All 19 sections generated |
| Vocabulary accuracy | 20% | Entries map to real files |
| Import chain validity | 15% | Chains trace to real modules |
| Secret safety | 15% | No API keys, passwords, or tokens leaked |
| Section size bounds | 10% | Each section 0.1–50KB |
| Structural integrity | 10% | Valid markdown, working TOC links |
| Checksum functionality | 5% | Re-run skips when nothing changed |

A full report is written to `.claude/project-map/reports/install-report.md`.

---

## Using the Developer Skill

After install, a skill is available:

```
/<your-project-slug>-developer
```

It reads `PROJECT_MAP.md` and uses the Quick Routing table to load only the 2-3 sections relevant to your current task — typically 5–20KB of context instead of 100KB+.

---

## Keeping the Map Current

The pre-commit hook regenerates the map automatically whenever source files change. To force a manual regeneration:

```bash
python .claude/project-map/generate.py --force
```

To re-grade the current output:

```bash
python .claude/project-map/grader.py
```

---

## Learned Vocabulary

Every AI session is mined for vocabulary. When you say "the numbers page" and the AI opens `DealAnalyzerV2.tsx`, that alias is recorded with a score (frequency × recency). Aliases with a score ≥ 5 appear in `17-learned-vocabulary.md` automatically.

Run the miner manually:

```bash
python .claude/project-map/mine-sessions.py
```

---

## Operational Runbook

`.claude/rules/operational-runbook.md` is loaded every session and grows over time. When you encounter a non-obvious operational issue, the developer skill prompts:

> "This looks like operational knowledge worth documenting. Want me to add it to the runbook? (Y/n)"

Entries follow a simple format: symptom → cause → fix. This is the anti-drift mechanism — knowledge that can't be derived from code lives here.

---

## File Structure

```
.claude/
├── project-map/
│   ├── generate.py              # Introspection script
│   ├── grader.py                # Quality grader
│   ├── mine-sessions.py         # Session vocabulary miner
│   ├── PROJECT_MAP.md           # TOC + quick routing guide
│   ├── sections/                # 19 focused section files
│   ├── reports/                 # Install and iteration reports
│   ├── checksums.json           # Skip regeneration if unchanged
│   └── learned-vocabulary.json  # Persisted session aliases
├── rules/
│   ├── project-vocabulary.md    # Auto-loaded every session
│   └── operational-runbook.md   # Auto-loaded every session
└── skills/
    └── <project>-developer-skill/
        └── SKILL.md
.githooks/
├── pre-commit                   # Auto-regenerates map on commit
└── install.sh                   # Register hooks: bash .githooks/install.sh
```

---

## Supported Stacks

| Language | Frameworks |
|----------|-----------|
| Python | FastAPI, Django, Flask |
| TypeScript / JavaScript | Next.js, NestJS, Express, React, Vue, Svelte |
| Go | Gin, Echo, Chi, stdlib |
| Java | Spring Boot |
| Any | docker-compose, nginx, Caddy, Terraform, Prisma, SQLAlchemy, TypeORM |

---

## Requirements

- AI coding assistant (Claude Code, Cursor, or compatible)
- Python ≥ 3.8 (auto-installed if missing)
- Bash
- Optional: `pip install pyyaml` for docker-compose YAML parsing (regex fallback included)

---

## Commands

| Command | What It Does |
|---------|-------------|
| `python .claude/project-map/generate.py --force` | Force-regenerate project map |
| `python .claude/project-map/grader.py` | Grade map quality (0–100%) |
| `python .claude/project-map/mine-sessions.py` | Mine session vocabulary |
| `bash .githooks/install.sh` | (Re)install git hooks |
| `bash .claude/install.sh` | Re-run full plugin installer |

---

## License

MIT — see [LICENSE](LICENSE)

---

**Made by [TheGlitchKing](https://github.com/TheGlitchKing)**
