---
title: Documentation Index
tier: reference
domains: [root]
status: active
last_updated: '2026-11-08'
version: '1.0.0'
generated: true
purpose: Navigation hub for all documentation
---

# Documentation Index

> Complete listing of all documentation organized by domain.

## Overview

| Domain | Documents | Description |
|--------|-----------|-------------|
| [Agents](#agents) | 0 | Expert agent documentation, specialty matrix |
| [API](#api) | 2 | API endpoints, routes, specifications, contracts |
| [Architecture](#architecture) | 3 | System design, AI coach, project registry, patterns |
| [Backups](#backups) | 0 | Backup/restore guides, disaster recovery |
| [Database](#database) | 0 | Schema, migrations, RLS, queries, procedures |
| [DevOps](#devops) | 0 | Deployment, CI/CD, Docker, environments, infrastructure |
| [Features](#features) | 0 | Feature implementation guides, admin docs |
| [Plans](#plans) | 0 | Planning documents, roadmaps, proposals |
| [Procedures](#procedures) | 1 | Step-by-step operational procedures (SOP) |
| [Quickstart](#quickstart) | 1 | Setup guides, dev workflow, onboarding |
| [Security](#security) | 0 | Security, auth, Vault, Keycloak, RLS |
| [Standards](#standards) | 2 | Coding standards (backend, frontend, database, devops, security) |
| [Testing](#testing) | 0 | Test strategies, fixtures, patterns, integration/e2e |
| [Troubleshooting](#troubleshooting) | 3 | Debug guides, common issues, solutions |
| [Workflows](#workflows) | 0 | Process documentation, multi-step operations |

---

## Agents

> Expert agent documentation, specialty matrix

**Path:** `agents/`

*No documents yet.*

---

## API

> API endpoints, routes, specifications, contracts

**Path:** `api/`

| Document | Tier | Status | Updated | Purpose |
|----------|------|--------|----------|---------|
| [Babel-fish glossary contract](api/glossary-contract.md) | reference | active | 2026-11-07 | The glossary.json artifact babel-fish emits for machine consumers, and the stability rules around it |
| [Skill parser contract](api/skill-parser-contract.md) | reference | active | 2026-09-04 | Which frontmatter fields SkillParser reads from skill and command manifests, and how they become vocabulary entries |

---

## Architecture

> System design, AI coach, project registry, patterns

**Path:** `architecture/`

| Document | Tier | Status | Updated | Purpose |
|----------|------|--------|----------|---------|
| [Grading semantics](architecture/grading-semantics.md) | reference | active | 2026-10-22 | What grader.py measures and what it deliberately does not, and why usefulness is warned about rather than scored |
| [Project map watch set](architecture/project-map-watch-set.md) | reference | active | 2026-11-07 | How generate.py decides which files can trigger a regeneration, and why the rules differ per file kind |
| [Session vocabulary mining](architecture/session-vocabulary-mining.md) | reference | active | 2026-09-04 | How mine-sessions.py turns Claude Code transcripts into learned aliases, and the transcript-shape assumptions it depends on |

---

## Backups

> Backup/restore guides, disaster recovery

**Path:** `backups/`

*No documents yet.*

---

## Database

> Schema, migrations, RLS, queries, procedures

**Path:** `database/`

*No documents yet.*

---

## DevOps

> Deployment, CI/CD, Docker, environments, infrastructure

**Path:** `devops/`

*No documents yet.*

---

## Features

> Feature implementation guides, admin docs

**Path:** `features/`

*No documents yet.*

---

## Plans

> Planning documents, roadmaps, proposals

**Path:** `plans/`

*No documents yet.*

---

## Procedures

> Step-by-step operational procedures (SOP)

**Path:** `procedures/`

| Document | Tier | Status | Updated | Purpose |
|----------|------|--------|----------|---------|
| [Changing repo structure](procedures/changing-repo-structure.md) | guide | active | 2026-09-30 | How to adopt the structure check, and recipes for adding, moving and retiring folders, apps, environments and repo pointers |

---

## Quickstart

> Setup guides, dev workflow, onboarding

**Path:** `quickstart/`

| Document | Tier | Status | Updated | Purpose |
|----------|------|--------|----------|---------|
| [Integration with semantic-memory](quickstart/integration-with-semantic-memory.md) | guide | active | 2026-11-07 | What babel-fish provides for semantic-memory to consume, and the current state of that integration |

---

## Security

> Security, auth, Vault, Keycloak, RLS

**Path:** `security/`

*No documents yet.*

---

## Standards

> Coding standards (backend, frontend, database, devops, security)

**Path:** `standards/`

| Document | Tier | Status | Updated | Purpose |
|----------|------|--------|----------|---------|
| [Auto-loaded context check](standards/auto-loaded-context-check.md) | standard | active | 2026-10-25 | Documentation for auto-loaded context check |
| [Repo structure check](standards/repo-structure-check.md) | standard | active | 2026-09-30 | Reference for .claude/structure.toml and structure-check.py -- folders, lifecycle, environments, repo pointers, CLI, hook and CI |

---

## Testing

> Test strategies, fixtures, patterns, integration/e2e

**Path:** `testing/`

*No documents yet.*

---

## Troubleshooting

> Debug guides, common issues, solutions

**Path:** `troubleshooting/`

| Document | Tier | Status | Updated | Purpose |
|----------|------|--------|----------|---------|
| [Learned vocabulary is empty](troubleshooting/learned-vocabulary-empty.md) | guide | active | 2026-09-04 | Why section 17 has no entries, and how to tell an expected empty result from a broken miner |
| [Project map is empty or stale](troubleshooting/map-is-empty.md) | guide | active | 2026-09-04 | Symptom-cause-fix for an empty project map, a map that will not regenerate, and a stale section 19 |
| [Structure check failures](troubleshooting/structure-check-failures.md) | guide | active | 2026-09-30 | Symptom-cause-fix for structure-check.py -- blocked commits, a check that never runs, unusable manifests, surprising detection |

---

## Workflows

> Process documentation, multi-step operations

**Path:** `workflows/`

*No documents yet.*

---

## Maintenance

- **Last generated:** 2026-11-08
- **Run maintenance:** `npx hit-em-with-the-docs maintain`
- **Regenerate index:** `npx hit-em-with-the-docs index`
