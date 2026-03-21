---
id: "CHUNK-009"
type: "chunk"
plan: "PLAN-011"
project: ""
title: "Status model cleanup"
status: "completed"
description: "Add failed status, circuit breaker, kill onward start, unify depends_on/blocked_by."
priority: "high"
model: "sonnet-latest"
estimated_files: 20
depends_on:
  - "CHUNK-008"
created_at: "2026-03-20T15:52:26Z"
updated_at: "2026-03-20T17:59:26Z"
---

# Summary

Fix the status model so AI agents can distinguish never-attempted from repeatedly-failing tasks, stop retrying broken work automatically, and have a single clear dependency mechanism. Remove the vestigial `onward start` command.

# Scope

- Add `failed` status: `onward work` sets this on executor failure instead of resetting to `open`
- Add `onward retry TASK-X` to reset failed → open
- Track `run_count` and `last_run_status` in task frontmatter
- Circuit breaker: `work.max_retries` config (default 3), refuse execution when exceeded
- Remove `onward start` command entirely
- Unify `depends_on` as sole dependency field; `blocked_by` becomes deprecated read alias
- Update LIFECYCLE.md, AGENTS.md, all error messages

# Out of scope

- Structured feedback from executor (chunk 4)
- Parallel execution
- Priority-based scheduling

# Dependencies

- CHUNK-008 (executor foundation must exist for `failed` status to be meaningful)

# Expected files/systems involved

- `src/onward/artifacts.py` — status transitions, dependency logic
- `src/onward/execution.py` — failed status, retry tracking, circuit breaker
- `src/onward/cli.py` — remove start, add retry
- `src/onward/cli_commands.py` — retry handler, remove start handler
- `docs/LIFECYCLE.md` — authoritative status docs
- All test files that reference `start` or status transitions

# Completion criteria

- [ ] Failed tasks show `failed` status in `onward report` / `onward tree`
- [ ] `onward next` never recommends a `failed` task
- [ ] `onward retry TASK-X` resets failed → open
- [ ] Circuit breaker refuses work after max_retries
- [ ] `onward start` is gone from CLI, parser, docs
- [ ] `blocked_by` in frontmatter is silently read as `depends_on`
- [ ] LIFECYCLE.md is the authoritative reference and matches code
