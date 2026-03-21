---
id: "TASK-037"
type: "task"
plan: "PLAN-005"
chunk: "CHUNK-011"
project: ""
title: "Create WorkReporter class with output methods and indentation context manager"
status: "in_progress"
description: ""
human: false
model: "sonnet"
executor: "onward-exec"
depends_on: []
files: []
acceptance: []
created_at: "2026-03-21T16:26:40Z"
updated_at: "2026-03-21T19:03:22Z"
run_count: 3
last_run_status: "model_error"
---

# Context

This is the foundational task for PLAN-005. We need a self-contained reporter class that encapsulates all progress output formatting for the `onward work` command. Once this exists, subsequent tasks wire it into the execution path.

# Scope

- Create `src/onward/reporter.py`
- Implement `WorkReporter` class with these methods:
  - `status_change(artifact_id, title, new_status)` — announces `▸ TASK-001 → in_progress  "Title"`
  - `working_on(artifact_id, title)` — announces `● Working on TASK-001  "Title"`
  - `completed(artifact_id, title)` — announces `✓ TASK-001 completed  "Title"`
  - `failed(artifact_id, title, reason="")` — announces `✗ TASK-001 failed  "Title"`
  - `skipped(artifact_id, title, reason="")` — announces `⊘ TASK-001 skipped  "Title"`
  - `plan_summary(plan_id, title, chunks, tasks)` — announces `✓ PLAN-001 completed (2 chunks, 4 tasks)`
  - `info(msg)` — general info line
  - `warning(msg)` — `⚠` prefixed warning
- Implement `indent()` context manager that increases/decreases indentation depth (2 spaces per level)
- Constructor takes `color: bool = True` (auto-detect from `sys.stdout.isatty()` and `NO_COLOR` env)
- Thread-safe `_write()` using `threading.Lock`
- Use `_colorize()` and `status_color()` from `src/onward/util.py`

# Out of scope

- Wiring into cli_commands.py or execution.py
- Tests (CHUNK-013)
- JSON output mode, quiet/verbose flags

# Files to inspect

- `src/onward/util.py` — existing `_colorize()` (line 111), `status_color()` (line 127)

# Implementation notes

- `_colorize` is module-private (underscore prefix). Either make it public or import it directly since reporter.py is in the same package.
- `status_color()` maps status strings to color names — use this for the status in `status_change()`
- The `indent()` context manager should be a simple `@contextmanager` that increments/decrements `self._indent`
- Unicode symbols: `▸` (U+25B8), `●` (U+25CF), `✓` (U+2713), `✗` (U+2717), `⊘` (U+2298), `⚠` (U+26A0)
- For `plan_summary`, use proper pluralization ("1 chunk" vs "2 chunks")

# Acceptance criteria

- [ ] `src/onward/reporter.py` exists with `WorkReporter` class
- [ ] All listed methods implemented
- [ ] `indent()` context manager correctly nests output
- [ ] Colors applied via existing util functions
- [ ] Thread-safe writes
- [ ] `NO_COLOR` env var respected

# Handoff notes

After this task, TASK-038/039/040 will import and use `WorkReporter` in the work command path.
