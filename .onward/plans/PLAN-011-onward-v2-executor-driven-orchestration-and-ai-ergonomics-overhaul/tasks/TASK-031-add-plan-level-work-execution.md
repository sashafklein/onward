---
id: "TASK-031"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-008"
project: ""
title: "Add plan-level work execution"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on:
  - "TASK-029"
blocked_by: []
files:
  - "src/onward/cli_commands.py"
  - "src/onward/execution.py"
  - "src/onward/artifacts.py"
  - "tests/test_cli_work.py"
acceptance:
  - "onward work PLAN-X drains all chunks and their tasks"
  - "onward work PLAN-X auto-completes the plan when all chunks finish"
  - "onward work PLAN-X stops on first chunk failure"
created_at: "2026-03-20T16:00:56Z"
updated_at: "2026-03-20T16:44:59Z"
---

# Context

Currently `onward work` accepts TASK-* and CHUNK-* IDs. The `cmd_work` function in cli_commands.py handles tasks directly and chunks by draining their ready tasks in order. This task adds PLAN-* support so that `onward work PLAN-X` drains all chunks belonging to the plan, each of which drains its tasks. This enables full top-down execution: one command to run an entire plan.

# Scope

- In `cli_commands.py` `cmd_work`: add a branch for `artifact_type == "plan"` before the existing chunk branch
- The plan-level work logic:
  1. Validate the plan is in `open` or `in_progress` status (same pattern as chunk)
  2. Set plan to `in_progress`
  3. Collect all chunks belonging to this plan (filter `collect_artifacts` by `type == "chunk"` and `plan == plan_id`)
  4. Sort chunks by ID (natural sort: CHUNK-008 before CHUNK-009), respecting `depends_on` if present
  5. Skip chunks that are already `completed` or `canceled`
  6. For each open/in_progress chunk, run the existing chunk work logic (the `while True` loop + post-hook + status update)
  7. If any chunk fails, stop and report which chunk failed
  8. After all chunks complete, auto-complete the plan
  9. Print a completion summary
- Refactor the chunk work logic in `cmd_work` into a reusable function (e.g., `_work_chunk(root, chunk) -> tuple[bool, str]`) so it can be called from both the chunk branch and the plan branch without duplicating code
- Update the error message for unsupported types: currently says "is not a task or chunk", should say "is not a task, chunk, or plan"
- Add tests for plan-level work in `test_cli_work.py`

# Out of scope

- Parallel chunk execution (sequential only, matching CHUNK-008 scope)
- Chunk dependency ordering beyond simple ID sort (complex DAG resolution is future work)
- Plan-level pre/post hooks (only task and chunk hooks exist today)
- Resuming a partially-completed plan from the middle (it naturally resumes because completed chunks are skipped)
- Changing the plan review flow (that's `review-plan`, not `work`)

# Files to inspect

- `src/onward/cli_commands.py` — `cmd_work` function (lines ~554-622): understand the current chunk work flow; this is where plan support is added
- `src/onward/execution.py` — `ordered_ready_chunk_tasks`, `work_task`, `run_chunk_post_markdown_hook`, `finalize_chunks_all_tasks_terminal`: these are the building blocks
- `src/onward/artifacts.py` — `collect_artifacts`, `update_artifact_status`, `must_find_by_id`: needed for plan status management
- `tests/test_cli_work.py` — understand existing test patterns for work command

# Implementation notes

- **Refactor chunk logic first**: Extract the chunk work loop (lines ~582-622 of cmd_work) into a helper like `_work_chunk(root: Path, chunk: Artifact, config: dict) -> int` that returns an exit code. The plan handler calls this in a loop.
- **Chunk ordering**: Sort by chunk ID string. If chunks have `depends_on` metadata, check that dependencies are completed before starting a chunk (same pattern as task dependency checking in `ordered_ready_chunk_tasks`). For now, simple ID sort is sufficient since chunks in PLAN-011 are numbered sequentially.
- **Plan status transitions**: Use `update_artifact_status(root, plan, "in_progress")` at start, `update_artifact_status(root, plan, "completed")` at end. If a chunk fails, leave the plan as `in_progress` (it can be resumed).
- **Completion message**: After all chunks complete, print something like `"Plan PLAN-X completed (N chunks, M tasks)"`. Count completed chunks and tasks for the summary.
- **Existing finalize logic**: After completing work, still call `finalize_chunks_all_tasks_terminal` to catch any chunks that became complete due to external task completions.
- **Edge cases**:
  - Plan with zero chunks: print "Plan PLAN-X has no chunks" and return 0 (or 1 — decide based on whether this is an error)
  - Plan already completed: print "Plan PLAN-X already completed" and return 0 (same as chunk behavior)
  - All chunks already completed: auto-complete the plan and return 0

# Acceptance criteria

- `onward work PLAN-X` on a plan with 2 chunks (each with 2 tasks) runs all 4 tasks in chunk order, completes both chunks, and completes the plan
- `onward work PLAN-X` on a plan where chunk 1 has a failing task: stops after the failure, chunk 1 remains `in_progress`, plan remains `in_progress`, chunk 2 is untouched
- `onward work PLAN-X` on a plan with one completed chunk and one open chunk: skips the completed chunk, runs only the open one
- `onward work PLAN-X` on an already-completed plan: prints "already completed" and exits 0
- The refactored chunk work logic still works correctly for `onward work CHUNK-X` (no behavioral regression)
- New test(s) in `test_cli_work.py` covering plan-level work happy path and failure case
- `onward work` with an unsupported artifact type (e.g., a run ID) shows an error mentioning task, chunk, and plan

# Handoff notes

The plan-level work handler is the keystone for full top-down execution. After this lands, the AGENTS.md loop (`onward work PLAN-X` or `onward work TASK-X`) covers all artifact types. The sequential execution is intentional — parallel chunk execution would require significant changes to ongoing.json tracking and is out of scope for CHUNK-008.
