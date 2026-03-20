---
id: "TASK-045"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-012"
project: ""
title: "Add batch task creation"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:08Z"
updated_at: "2026-03-20T16:01:08Z"
---

# Context

CHUNK-012 adds scale ergonomics. Currently creating multiple tasks requires repeated `onward new task` calls, each writing one file and regenerating indexes. This is slow and awkward for AI agents that want to enqueue a batch of tasks. This task adds `--batch` support: read a JSON array of task definitions from a file and create them all in one operation with a single index regeneration.

# Scope

- Add `--batch` flag to the `task` sub-parser of `onward new` in `cli.py`, accepting a file path
- Add `cmd_new_task_batch(root, chunk_id, batch_path, project)` in `cli_commands.py`
- Batch JSON format: array of objects, each with `{title, description, model?, human?, depends_on?, files?, acceptance?, effort?}`
- Assign IDs sequentially using `next_ids(root, "TASK", count)`
- Resolve `depends_on` references: support both existing task IDs (`TASK-034`) and intra-batch indices (`$0`, `$1`) for tasks created in the same batch
- Write all task files, then regenerate indexes once
- Print all created task IDs and paths
- Validate batch input: all entries must have `title` and `description`; error on the entire batch if any entry is invalid (atomic — all or nothing)
- Add tests for batch creation, intra-batch dependencies, validation errors

# Out of scope

- Batch chunk creation (only tasks)
- Batch updates to existing tasks
- Reading batch input from stdin (file path only)
- Interactive editing of batch entries

# Files to inspect

- `src/onward/cli.py` — `task_parser` (line ~98) for `--batch` flag
- `src/onward/cli_commands.py` — `cmd_new_task()` for the single-task creation pattern to replicate
- `src/onward/artifacts.py` — `next_ids()` for batch ID assignment, `find_plan_dir()`, `format_artifact()`, `regenerate_indexes()`
- `src/onward/split.py` — `prepare_task_writes()` for a similar batch-write pattern
- `src/onward/util.py` — `slugify`, `now_iso`

# Implementation notes

- The batch flag and the positional `title` arg are mutually exclusive. When `--batch` is provided, `title` is not required. Use argparse mutually exclusive groups or handle in the command handler.
- Intra-batch `depends_on` resolution: entries can reference other batch entries by index using `$N` syntax (e.g., `"depends_on": ["$0"]` means "depends on the first task in this batch"). After IDs are assigned, replace `$N` with the actual task ID.
- The `next_ids` function already exists and returns a list of sequential IDs. Use it to pre-allocate all IDs before writing.
- Validation should happen before any writes. Load the JSON, validate all entries, assign IDs, resolve dependencies, then write.
- Reuse the metadata shape from `cmd_new_task` — same fields, same defaults.
- The `--batch` flag value should be a file path. Read and parse it as JSON. If the file doesn't exist or isn't valid JSON, error clearly.
- Consider: should batch support `--dry-run`? Probably yes — it's useful for validation. Add `--dry-run` to the task sub-parser when `--batch` is used.

# Acceptance criteria

- `onward new task CHUNK-X --batch tasks.json` creates all tasks from the JSON array
- All task IDs are assigned sequentially
- Intra-batch `depends_on` references (`$0`, `$1`) resolve to actual task IDs
- External `depends_on` references (`TASK-034`) pass through unchanged
- Index is regenerated once (not per task)
- Invalid batch input (missing title) errors before any files are written
- Created tasks are printed to stdout with IDs and paths
- Tests cover: basic batch, intra-batch deps, validation failure, empty batch

# Handoff notes

- This pairs well with AI-driven split (CHUNK-010): split produces JSON, batch creation consumes it. A future `onward split --apply` could pipe split output directly to batch creation.
- The `$N` syntax for intra-batch references is a convention choice. Alternative: use titles. Index-based is simpler and unambiguous.
- The `effort` field from the batch input ties into TASK-047 (effort metadata). If TASK-047 hasn't landed, ignore `effort` in batch input (don't error, just skip it).
