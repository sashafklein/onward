---
id: "TASK-047"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-012"
project: ""
title: "Add effort and size metadata"
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

Tasks and chunks currently have no size or effort indication. An AI agent can't distinguish a 30-minute task from a 3-hour one without reading the full body. This task adds `effort` metadata to tasks and chunks, plus `estimated_files` for chunks, enabling better work ordering and progress estimation.

# Scope

- Add `effort` field to task metadata schema: valid values `"xs"`, `"s"`, `"m"`, `"l"`, `"xl"` (optional, default empty)
- Add `effort` field to chunk metadata schema: same values
- Add `estimated_files` field to chunk metadata: integer (optional, default 0)
- Add `--effort` flag to `onward new task` and `onward new chunk` CLI subparsers
- Add `--estimated-files` flag to `onward new chunk`
- Store these fields in artifact metadata when creating new artifacts
- Display effort in `onward report` — show aggregate effort remaining (count by effort level)
- Display effort in `onward show` output
- Add `normalize_effort(value)` in `util.py` that validates and normalizes the effort string
- Update task and chunk templates in scaffold to include `effort` field (commented out or empty)
- Add tests for effort metadata, normalization, and display

# Out of scope

- Effort-based sorting in `onward next` or `onward ready` (display only for now)
- Automatic effort estimation from task body
- Time tracking or actual-vs-estimated reporting
- Changing how IDs are assigned based on effort

# Files to inspect

- `src/onward/cli.py` — `task_parser` and `chunk_parser` for new flags
- `src/onward/cli_commands.py` — `cmd_new_task()`, `cmd_new_chunk()`, `cmd_show()`, `cmd_report()`
- `src/onward/util.py` — add `normalize_effort()`
- `src/onward/scaffold.py` — `DEFAULT_FILES` for template updates
- `src/onward/split.py` — `prepare_task_writes()`, `prepare_chunk_writes()` for including effort in generated artifacts

# Implementation notes

- `normalize_effort` should accept the string and return the normalized form. Invalid values should return empty string (not error). Valid: `xs`, `s`, `m`, `l`, `xl` (case-insensitive).
- In `cmd_report`, add a section like:
  ```
  [Effort remaining]
  xs: 3  s: 5  m: 2  l: 1  xl: 0  unestimated: 4
  ```
  Count only open/in_progress tasks.
- The `--effort` flag on `new task` and `new chunk` should accept a string value. If invalid, print a warning and use empty.
- `estimated_files` on chunks is informational — Onward doesn't enforce it. It's useful for AI agents deciding how to approach a chunk.
- The split system (TASK-039's prompt rewrite) should suggest `effort` values. `prepare_task_writes` should pass through `effort` from split output if available.
- Don't make `effort` required anywhere — it's always optional.

# Acceptance criteria

- `onward new task CHUNK-X "title" --effort m` stores `effort: "m"` in metadata
- `onward new chunk PLAN-X "title" --effort l --estimated-files 25` stores both
- `onward show TASK-X` displays effort if set
- `onward report` shows effort remaining summary for open/in_progress tasks
- `normalize_effort("M")` returns `"m"`, `normalize_effort("invalid")` returns `""`
- Templates include effort field
- Tests cover: creation with effort, normalization, report display

# Handoff notes

- This is a metadata-only task — it adds fields but doesn't change execution behavior.
- TASK-046 (onward ready) can optionally display effort if this task lands first.
- Future enhancement: `onward next --quickest` that picks the smallest-effort ready task.
- The effort values (`xs`/`s`/`m`/`l`/`xl`) are T-shirt sizes. No numeric mapping is defined — agents interpret them contextually.
