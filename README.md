# Onward

**The rails your AI runs on.**

Onward is a git-native CLI that gives AI agents a structured, markdown-first system for planning, decomposing, tracking, and executing software development work. Every plan, every task, every status change — committed to the repo, diffable, reviewable, never lost.

No more plans that vanish when a chat session ends. No more context scattered across threads. No more "what was I working on?" after a handoff. Onward keeps the train moving.

---

## What This Is

Onward is a **process manager for AI-driven development.** It enforces a simple, powerful hierarchy:

```
Plan  →  Chunk  →  Task
 ↓         ↓         ↓
 why      what      how
```

- A **Plan** is a high-level initiative. The big picture. _"Rewrite the auth system."_
- A **Chunk** is a bounded deliverable within a plan. One PR-sized piece. _"Backend token flow."_
- A **Task** is the smallest executable unit. One clear job. _"Add session table migration."_

Everything is a markdown file with YAML frontmatter. Everything lives in `.onward/plans/`. Everything is versioned in git. The source of truth is always the filesystem.

## What This Is Not

- Not a web app. Not a database. Not a ticketing system.
- Not a chat plugin or a wrapper around an LLM.
- Not a generic PM tool for large teams.

Onward is an **opinionated, single-developer momentum engine** for repos where AI does the heavy lifting and structure is what keeps it on the rails.

---

## The Loop

This is the heartbeat of Onward-driven development:

```
┌─────────────────────────────────────────┐
│                                         │
│   1.  onward report        ← see where you are
│   2.  onward next          ← pick what's next
│   3.  onward start TASK-X  ← claim it
│   4.  ... do the work ...
│   5.  onward complete TASK-X
│   6.  goto 1               ← keep moving
│                                         │
└─────────────────────────────────────────┘
```

Every cycle tightens the loop. Every artifact records what happened. Nothing falls through the cracks.

---

## Install

Requires Python 3.11+.

```bash
cd /path/to/onward-repo
python3.11 -m pip install -e .
```

Verify:

```bash
onward --help
```

Then, in any project where you want to use Onward:

```bash
cd /path/to/your-project
onward init
onward doctor
```

That's it. You're on the rails.

See **[INSTALLATION.md](INSTALLATION.md)** for full setup including **agent configuration** — the critical step that makes your AI agents use Onward for all planning and execution tracking.

---

## Commands at a Glance

### Creating Work

| Command                                 | What it does                    |
| --------------------------------------- | ------------------------------- |
| `onward new plan "Title" --project key` | Create a new plan               |
| `onward new chunk PLAN-001 "Title"`     | Add a chunk to a plan           |
| `onward new task CHUNK-001 "Title"`     | Add a task to a chunk           |
| `onward split PLAN-001`                 | AI-decompose a plan into chunks |
| `onward split CHUNK-001`                | AI-decompose a chunk into tasks |

### Seeing What's Happening

| Command                       | What it does                      |
| ----------------------------- | --------------------------------- |
| `onward report --project key` | Full status dashboard             |
| `onward list --project key`   | List all artifacts                |
| `onward tree --project key`   | Hierarchical plan/chunk/task tree |
| `onward next --project key`   | What should be worked on next     |
| `onward progress`             | What's currently in flight        |
| `onward recent`               | What just got done                |
| `onward show TASK-001`        | Full detail on one artifact       |

### Moving Work Forward

| Command                    | What it does                              |
| -------------------------- | ----------------------------------------- |
| `onward start TASK-001`    | Mark as in-progress                       |
| `onward complete TASK-001` | Mark as done                              |
| `onward cancel TASK-001`   | Mark as canceled                          |
| `onward work TASK-001`     | Execute task                              |
| `onward work CHUNK-001`    | Execute all tasks in a chunk sequentially |
| `onward archive PLAN-001`  | Archive a completed plan                  |

### Filtering

```bash
onward list --project alpha --blocking    # what's blocking progress
onward list --project alpha --human       # what needs a human
onward list --blocking --human            # human actions blocking agents
```

---

## Artifact Anatomy

Every artifact is a markdown file with structured frontmatter:

```yaml
---
id: TASK-007
type: task
plan: PLAN-002
chunk: CHUNK-003
project: auth-rewrite
title: Add refresh token rotation
status: open
human: false
blocked_by: []
created_at: 2026-03-18T12:00:00Z
---

# Context
Refresh tokens currently never rotate...

# Scope
- Add rotation logic to /api/auth/refresh
- Invalidate old token on use

# Acceptance criteria
- Tokens rotate on every refresh call
- Old tokens are rejected
- Tests pass
```

Status flows: `open` → `in_progress` → `completed` (or `canceled`)

---

## Repo Layout

When you run `onward init`, your project gets:

```
.onward.config.yaml              ← workspace config (path, models, hooks, sync)
.onward/
  plans/
    index.yaml                   ← derived index (regenerable)
    recent.yaml                  ← recently completed
    PLAN-001-auth-rewrite/
      plan.md
      chunks/
        CHUNK-001-backend.md
      tasks/
        TASK-001-schema.md
        TASK-002-endpoints.md
    .archive/                    ← archived plans (gitignored)
  templates/                     ← markdown templates for new artifacts
  hooks/                         ← pre/post execution hooks
  prompts/                       ← prompts for split decomposition
  runs/                          ← execution records (gitignored)
  sync/                          ← sync workspace state
```

Plans are the filesystem. The filesystem is the truth.

---

## The Agent Integration (This Is the Important Part)

Onward is built to be used **by AI agents** as their primary planning and tracking system. The whole point is that your agent — whether it's Claude, GPT, Codex, OpenClaw, or anything else — treats Onward as the **single source of truth** for what to do, what's happening, and what's done.

**See [INSTALLATION.md](INSTALLATION.md)** for:

- Exact text blocks to paste into your agent's `AGENTS.md` / `SOUL.md` / system prompt
- A ready-to-use `SKILL.md` template
- The agent operating policy
- First-run walkthrough

If you skip agent setup, you have a nice CLI. If you do it, you have **structured, persistent, git-tracked AI development with full context continuity across sessions.**

---

## Key Concepts

### Forward Momentum

Onward is named for its core value: **keep moving forward.** Every command either shows you the state of the world or advances it. `report` → `next` → `start` → `complete` → `report`. The loop never stops.

### Feedback Capture

During execution, new work always surfaces — blockers, refactors, follow-ups. Onward expects this. Agents should immediately capture discovered work as new tasks with `blocked_by`, `human`, and `project` metadata. Nothing gets lost in a chat log.

### Markdown Native

Every artifact is a markdown file you can open, read, and edit in any editor. No opaque databases. No proprietary formats. Just files, in a repo, under version control.

### Git Native

Plans live alongside code. They can be committed, branched, diffed, reviewed, and merged. When you `git log`, you see the planning history right next to the implementation history.

---

## Development

### Testing

```bash
pip install -e '.[dev]'
pytest
```

Or use the convenience script:

```bash
./scripts/test.sh
```

### Dogfooding

Bootstrap a consumer workspace that uses this repo as the source:

```bash
./scripts/dogfood/bootstrap.sh
./scripts/dogfood/e2e.sh
```

---

## Documentation

| Doc                                                                        | What it covers                     |
| -------------------------------------------------------------------------- | ---------------------------------- |
| [INSTALLATION.md](INSTALLATION.md)                                         | Install + agent setup (start here) |
| [docs/NOOB_GUIDE.md](docs/NOOB_GUIDE.md)                                   | First-time contributor walkthrough |
| [docs/spec/onward_v1_product_spec.md](docs/spec/onward_v1_product_spec.md) | Full v1 product specification      |
| [docs/architecture/work-handoff.md](docs/architecture/work-handoff.md)     | How execution handoff works        |
| [docs/dogfood/README.md](docs/dogfood/README.md)                           | Dogfood workflow details           |

---

_Plans are cheap. Execution is everything. Stay on the rails. Move onward._
