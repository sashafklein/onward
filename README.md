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
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   1.  onward report           ← see where you are        │
│   2.  onward next             ← pick what's next           │
│   3.  onward start TASK-X     ← optional: claim / visibility │
│   4.  onward work TASK-X      ← executor + status (success → completed) │
│   5.  onward report           ← session handoff          │
│   6.  goto 1                  ← keep moving                │
│                                                          │
│   Use onward complete when closing work without work.    │
│   See docs/LIFECYCLE.md for the full policy.             │
│                                                          │
└──────────────────────────────────────────────────────────┘
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
| `onward split PLAN-001`                 | Heuristic plan→chunks (markdown-derived; [capabilities](docs/CAPABILITIES.md)) |
| `onward split CHUNK-001`                | Heuristic chunk→tasks (same) |
| `onward review-plan PLAN-001`           | Run adversarial review(s) of a plan |

### Seeing What's Happening

| Command                       | What it does                      |
| ----------------------------- | --------------------------------- |
| `onward report --project key` | Full status dashboard             |
| `onward list --project key`   | List all artifacts                |
| `onward tree --project key`   | Hierarchical plan/chunk/task tree |
| `onward next --project key`   | What should be worked on next     |
| `onward progress`             | What's currently in flight        |
| `onward recent`               | What just got done (artifacts + runs) |
| `onward show TASK-001`        | Full detail on one artifact (+ latest run for tasks) |
| `onward note TASK-001`        | View notes on an artifact         |

### Syncing plan files (optional)

Use this when you want a **second git checkout** (same repo, different branch, or another clone) to hold a copy of `.onward/plans/` that you can push to a remote—handy for sharing plan state across machines or with a separate “planner” repo.

Configure `sync` in `.onward.config.yaml`:

| `sync.mode` | Behavior |
| ----------- | -------- |
| `local` | Default. No remote target; `onward sync push` / `pull` are rejected with a hint. |
| `branch` | Creates or uses a [git worktree](https://git-scm.com/docs/git-worktree) at `sync.worktree_path` on `sync.branch` inside the **same** repository. Requires a `.git` directory at the workspace root. |
| `repo` | `git clone` of `sync.repo` (URL or path) into `sync.worktree_path`. |

The sync checkout path defaults to **`.onward/sync/`**; it is **gitignored** by `onward init` so nested checkouts do not dirty your main tree.

What gets synchronized:

- The **entire** `.onward/plans/` tree (plan folders, `index.yaml`, `recent.yaml`, `.archive/`, etc.) is **mirrored** file-by-file: extra files on the destination side are removed so the tree matches the source.
- **`onward sync push`** — copy workspace → sync checkout → `git add` under `.onward/plans` → commit if needed → `git push -u origin HEAD`. Needs a configured **`origin`** on that checkout and a remote that accepts the push (e.g. **bare** remote, or a branch that is not the remote’s checked-out branch).
- **`onward sync pull`** — `git pull --ff-only` in the sync checkout, then copy remote plans → workspace and **regenerate indexes**. If the remote has diverged, fix it in the sync checkout and retry.
- **`onward sync status`** — Compares local vs remote plan files (content hashes). Does **not** create the worktree or clone until you have run **`onward sync push`** at least once; until then it reports that the sync target is not initialized.

`onward doctor` checks `sync:` for consistency (e.g. `branch` mode without a git repo, missing `repo` in `repo` mode).

| Command                  | What it does                                                |
| ------------------------ | ----------------------------------------------------------- |
| `onward sync status`     | Clean / dirty vs sync target, or “not initialized”          |
| `onward sync push`       | Mirror local → target, commit, `git push`                     |
| `onward sync pull`       | Fast-forward target, mirror → workspace, reindex            |

### Moving Work Forward

Status rules: **[docs/LIFECYCLE.md](docs/LIFECYCLE.md)** — `onward work` advances task/chunk status around the executor; `start` is optional; use `complete` when closing work **without** `work`.

| Command                    | What it does                              |
| -------------------------- | ----------------------------------------- |
| `onward start TASK-001`    | Mark as in-progress (optional before `work`) |
| `onward complete TASK-001` | Mark done without running executor        |
| `onward cancel TASK-001`   | Mark as canceled                          |
| `onward work TASK-001`     | Run executor; on success task → completed |
| `onward work CHUNK-001`    | Run ready chunk tasks (dep-aware; set `work.sequential_by_default: false` for one task per invocation) |
| `onward archive PLAN-001`  | Archive a completed plan                  |
| `onward note ID "message"` | Add a note to any artifact                |

### Filtering

```bash
onward list --project alpha --blocking    # what's blocking progress
onward list --project alpha --human       # what needs a human
onward list --blocking --human            # human actions blocking agents
```

### Reviewing Plans

Before splitting or starting work on a plan, run an adversarial review:

```bash
onward review-plan PLAN-001
```

This spawns independent model-backed reviewers that scrutinize the plan for gaps, security issues, missing requirements, and deployment risks. Each reviewer produces a structured markdown report with severity-rated findings.

By default, **two reviewers** run using different models (`review_default` and `default` from config) so the reviews cross-validate each other. Set `review.double_review: false` in `.onward.config.yaml` to use a single reviewer.

Review artifacts are written to `.onward/reviews/` (gitignored — they're working documents, not permanent artifacts). The command announces the file paths and recommends you read through the findings and incorporate them into the plan before proceeding.

### Notes (Artifact Scratch Pad)

Any artifact — plan, chunk, or task — can have timestamped notes attached to it:

```bash
# Add a note
onward note TASK-001 "todo: check edge case for empty input"
onward note PLAN-002 "revisit auth approach after spike"

# View notes
onward note TASK-001
```

Notes are stored in `.onward/notes/{ID}.md`, one file per artifact, with timestamped entries appended as you go. When a note is added, the artifact's frontmatter gains `has_notes: true` so it's visible in metadata.

When you **complete** or **cancel** an artifact, its notes are printed inline:

```
TASK-001 status: in_progress -> completed

Related notes for TASK-001:

## 2026-03-19T12:00:00Z

todo: check edge case for empty input
```

This ensures that scratch-pad thoughts, TODOs, and observations surface at exactly the moment they matter — when work is being closed out. During `onward work`, notes are also included in the executor payload so the agent has full context.

### Execution Visibility

When tasks are executed via `onward work`, Onward tracks every run:

```bash
# See what's in flight right now
onward progress

# See recently completed artifacts AND run records
onward recent

# Inspect a task — includes its latest run info
onward show TASK-001
```

`onward show` on a task displays the latest run's ID, status, timestamps, log path, and error (if any):

```
Latest run:
  id: RUN-2026-03-19T23-51-00Z-TASK-001
  status: completed
  started_at: 2026-03-19T23:51:00Z
  finished_at: 2026-03-19T23:51:12Z
  log: .onward/runs/RUN-2026-03-19T23-51-00Z-TASK-001.log
```

`onward recent` interleaves completed artifacts with terminal run records, giving a unified timeline of what just happened.

The executor receives a rich context packet containing the task body, its parent chunk, and the parent plan — so the worker agent always knows the bigger picture without needing to read the filesystem.

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

Status flows: `open` → `in_progress` → `completed` (or `canceled`). **`onward work`** applies these transitions around executor runs; **`start` / `complete` / `cancel`** are manual. Details: **[docs/LIFECYCLE.md](docs/LIFECYCLE.md)**.

---

## Repo Layout

When you run `onward init`, your project gets:

```
.onward.config.yaml              ← workspace config (models, hooks, sync, work, ralph, …)
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
  prompts/                       ← prompts for split decomposition and reviews
  notes/                         ← per-artifact scratch pad notes
  runs/                          ← execution records (gitignored)
  reviews/                       ← plan review artifacts (gitignored)
  sync/                          ← optional sync git checkout (gitignored)
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

### Model vs local behavior

Not every command calls your configured executor. **`onward split`** is **heuristic** (markdown sections → structured candidates) unless you inject test JSON via `TRAIN_SPLIT_RESPONSE`. **`onward work`** and **`onward review-plan`** use the executor when enabled. Full table: **[docs/CAPABILITIES.md](docs/CAPABILITIES.md)**.

### Forward Momentum

Onward is named for its core value: **keep moving forward.** Every command either shows you the state of the world or advances it. A typical execution loop is `report` → `next` → `work` → `report`, with optional `start` for claiming and `complete` when not using `work`. See **[docs/LIFECYCLE.md](docs/LIFECYCLE.md)**.

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
| [INSTALLATION.md](INSTALLATION.md)                                         | Install + agent setup + sync semantics & troubleshooting |
| [docs/CONTRIBUTION.md](docs/CONTRIBUTION.md)                               | Contributor guide & local dev walkthrough |
| [docs/LIFECYCLE.md](docs/LIFECYCLE.md)                                     | Artifact status: `start` / `work` / `complete` / `cancel` |
| [docs/CAPABILITIES.md](docs/CAPABILITIES.md)                             | Model-backed vs local/heuristic commands   |
| **`.onward/plans/`**                                                      | Plans, chunks, tasks, acceptance criteria (source of truth) |
| [docs/WORK_HANDOFF.md](docs/WORK_HANDOFF.md)                               | Execution handoff design                    |
| [docs/schemas/onward-executor-stdin-v1.schema.json](docs/schemas/onward-executor-stdin-v1.schema.json) | Executor stdin JSON (versioned)             |
| [docs/DOGFOOD.md](docs/DOGFOOD.md)                                         | Dogfood workflow                            |

---

_Plans are cheap. Execution is everything. Stay on the rails. Move onward._
