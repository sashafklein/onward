---
id: "TASK-053"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-013"
project: ""
title: "Create FUTURE_ROADMAP.md"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:10Z"
updated_at: "2026-03-20T21:03:13Z"
---

# Context

Throughout PLAN-011 execution, ideas for future work were deferred. This task creates `docs/FUTURE_ROADMAP.md` as a structured parking lot for those ideas, plus broader vision items. This prevents deferred work from being lost and gives future planning sessions a starting point.

# Scope

- Create `docs/FUTURE_ROADMAP.md` with these sections:
  - **Parallel execution**: parallel task execution within chunks (worktree-per-task), parallel chunk execution (worktree-per-chunk)
  - **Daemon / orchestrator mode**: long-running daemon that monitors artifact status and auto-executes ready work
  - **Incremental index**: update index.yaml incrementally instead of full regeneration on every write
  - **Cross-workspace dependencies**: artifacts that depend on artifacts in other Onward workspaces
  - **Web dashboard**: read-only web UI for monitoring plan progress and run history
  - **Executor ecosystem**: pluggable executor framework, marketplace of executor scripts, model-specific routing
  - **Plan-level hooks**: `pre_plan_shell`, `post_plan_markdown` for plan-level orchestration
  - **Migration tooling**: `onward migrate` command for schema upgrades, `blocked_by` → `depends_on` rewriting
  - **Per-task config overrides**: `max_retries`, `timeout`, `executor` per-task in frontmatter
  - **Metrics and reporting**: execution time tracking, success rate dashboards, cost estimation
  - **Template system**: user-defined artifact templates beyond the defaults
  - **Plugin system**: loadable Python plugins for custom commands and hooks
- Each item should have: title, 2-3 sentence description, rough complexity/effort indication, and any prerequisite work
- Add a reference to `docs/FUTURE_ROADMAP.md` from `README.md`
- Reference it from `AGENTS.md` as the place to park deferred ideas

# Out of scope

- Implementing any of the roadmap items
- Prioritizing or ordering the roadmap (it's a flat parking lot)
- Creating Onward plans/chunks/tasks for roadmap items

# Files to inspect

- `docs/FUTURE_ROADMAP.md` — new file to create
- `README.md` — add reference
- `AGENTS.md` — add reference for deferred work parking
- `docs/` — scan existing docs for any deferred/future mentions to consolidate

# Implementation notes

- Keep the tone practical: each item should feel like it could be a plan summary, not a wish list. Include enough detail that a future session could turn it into an Onward plan.
- Organize by theme (execution, infrastructure, UX, ecosystem) rather than priority.
- Include items discovered during PLAN-011 execution:
  - Exponential backoff for retries (from TASK-035)
  - Per-task max_retries (from TASK-035)
  - `onward migrate` for schema changes (from TASK-037)
  - `--auto-fix` for split validation (from TASK-040)
  - Effort-based sorting in `onward next` (from TASK-047)
  - Multi-value project filtering (from TASK-048)
  - Incremental index updates (from TASK-049)
  - Plan-level hooks (from TASK-052)
- Keep the doc under 150 lines. Each item gets 3-5 lines max.
- Add a last-updated date at the top so future readers know how stale it is.

# Acceptance criteria

- `docs/FUTURE_ROADMAP.md` exists with all specified sections
- Each item has title, description, complexity, and prerequisites
- Items from PLAN-011 deferred work are included
- Referenced from `README.md` and `AGENTS.md`
- Doc is under 150 lines, organized by theme
- Last-updated date at the top

# Handoff notes

- This is a documentation-only task and can be done at any point during CHUNK-013.
- The roadmap is not a commitment — it's a parking lot. Make this clear in the doc header.
- Future planning sessions should start by reading this doc and deciding which items to promote to Onward plans.
- Consider: should `onward report` mention the roadmap doc? Probably not — it's a reference, not active work.
