---
id: "TASK-024"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-004"
project: ""
title: "Fix chunk completion and next selection semantics"
status: "completed"
description: "Auto-complete chunks with no actionable tasks and prevent next from selecting dead chunks"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:52Z"
updated_at: "2026-03-20T14:12:41Z"
---

# Context

PLAN-010 phase 2 **§5** UX bugs: **chunk completion** when all child tasks are completed; **`onward next`** must not return **non-actionable** items (e.g. chunks that cannot be progressed without human steps).

# Scope

- Fix `_select_next_artifact` / chunk status rules so `next` surfaces actionable work; align chunk auto-completion with LIFECYCLE when all tasks terminal.
- Add regression tests for reported bad states.

# Out of scope

- Tree labeling (TASK-025/026); split dry-run labels (TASK-027).

# Files to inspect

- `src/onward/artifacts.py` (`_select_next_artifact`, index helpers), `src/onward/cli.py` (`cmd_next`), `src/onward/execution.py` (chunk work completion), `tests/`

# Implementation notes

- Cross-check `human`, `blocked_by`, `depends_on` when ranking “next”.

# Acceptance criteria

- Tests encode expected `next` behavior; chunk completion matches documented intent in LIFECYCLE/README.

# Handoff notes

- `finalize_chunks_all_tasks_terminal` in `execution.py`: when every child task is `completed`/`canceled`, run `post_chunk` hook then mark chunk `completed`. Called from `next`, `report`, `complete` (any artifact), and after successful `work TASK-*`.
- `select_next_artifact`: tasks use `task_is_next_actionable` (includes `in_progress`, excludes human-only, respects deps/blocked_by); open chunks only if `chunk_has_actionable_executor_task`.
- `work CHUNK-*`: early return if chunk already completed; skip duplicate hook if finalized via per-task path.
- Docs: `docs/LIFECYCLE.md`; tests in `tests/test_cli_artifacts.py`.
