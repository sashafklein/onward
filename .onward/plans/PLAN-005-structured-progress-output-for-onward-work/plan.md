---
id: "PLAN-005"
type: "plan"
project: ""
title: "Structured progress output for onward work"
status: "in_progress"
description: ""
priority: "medium"
model: "opus-latest"
created_at: "2026-03-21T16:25:02Z"
updated_at: "2026-03-21T18:49:20Z"
---

# Summary

When running `onward work` on a plan (or chunk), the user currently sees minimal, inconsistent output — just run IDs and completion messages. This plan adds a structured progress reporter that announces every status transition with artifact titles, colored output, and hierarchical indentation so the user can follow exactly what's happening.

# Problem

Running `onward work PLAN-001` produces sparse output like `Run run_20250301_...: completed`. There's no indication of which plan/chunk/task is being set to in_progress, no artifact titles shown, no visual hierarchy, and the existing `colorize`/`status_color` utilities from `util.py` aren't used in the work path at all.

# Goals

- Every status transition during `onward work` is announced with artifact ID, title, and new status
- Output is visually hierarchical: plan → chunk → task indentation
- Colored output using existing ANSI utilities, respecting NO_COLOR / tty detection
- The reporter is a clean abstraction that can be swapped (for tests, JSON output, quiet mode)
- Replace all bare `print()` calls in the work path with reporter methods

# Non-goals

- Rich TUI / progress bars / spinners (future work)
- JSON structured output mode (the reporter pattern enables this later, but not in scope)
- `--quiet` / `--verbose` CLI flags (trivial to add later with the reporter, but not now)

# End state

- [ ] Running `onward work PLAN-XXX` shows plan/chunk/task status transitions with titles and colors
- [ ] Running `onward work CHUNK-XXX` shows chunk/task status transitions
- [ ] Running `onward work TASK-XXX` shows task status transitions
- [ ] Failed tasks show clear failure indication
- [ ] Skipped/retried tasks are announced
- [ ] Plan completion shows a summary line (e.g. "PLAN-001 completed (2 chunks, 4 tasks)")
- [ ] Tests validate reporter output formatting
- [ ] No regressions in existing test suite

# Context

The work command flow lives in two files:
- `src/onward/cli_commands.py`: `cmd_work`, `_work_plan` (plan loop, ~80 lines)
- `src/onward/execution.py`: `work_chunk`, `_work_chunk_loop`, `work_task`, `_finalize_task_run` (chunk/task execution, ~300 lines)

Status transitions happen via `update_artifact_status()` from `artifacts.py`. The existing `_colorize()` and `status_color()` in `util.py` handle ANSI coloring but are only used by `report`/`tree`/`show` commands today.

There are ~20 bare `print()` calls across these two files that need to be replaced.

# Proposed approach

## 1. WorkReporter class (new file: `src/onward/reporter.py`)

A class that encapsulates all progress output for the work command:

```python
class WorkReporter:
    def __init__(self, color: bool = True):
        self._color = color
        self._indent = 0

    def status_change(self, artifact_id: str, title: str, new_status: str): ...
    def working_on(self, artifact_id: str, title: str): ...
    def completed(self, artifact_id: str, title: str): ...
    def failed(self, artifact_id: str, title: str, reason: str = ""): ...
    def skipped(self, artifact_id: str, title: str, reason: str = ""): ...
    def plan_summary(self, plan_id: str, title: str, chunks: int, tasks: int): ...
    def info(self, msg: str): ...
    def warning(self, msg: str): ...

    def indent(self) -> ContextManager: ...  # context manager for nesting
```

Output format:

```
▸ PLAN-001 → in_progress  "Docs clarity overhaul"
  ▸ CHUNK-001 → in_progress  "Fix factual errors"
    ▸ TASK-001 → in_progress  "Fix AI operator anti-pattern"
    ● Working on TASK-001  "Fix AI operator anti-pattern"
    ✓ TASK-001 completed  "Fix AI operator anti-pattern"
  ✓ CHUNK-001 completed  "Fix factual errors"
✓ PLAN-001 completed (1 chunk, 1 task)
```

Symbols: `▸` status change, `●` working, `✓` completed, `✗` failed, `⊘` skipped, `⚠` warning.

## 2. Thread reporter through the work path

- `cmd_work()` in `cli_commands.py` creates a `WorkReporter` and passes it to `_work_plan` / `_work_chunk` / `work_task`
- `_work_plan` uses reporter for plan-level transitions, passes to `_work_chunk`
- `work_chunk` / `_work_chunk_loop` in `execution.py` accept a reporter parameter, use it for chunk/task transitions
- `work_task` in `execution.py` accepts a reporter parameter
- `_finalize_task_run` / `_run_hooked_executor_batch` accept a reporter parameter for completion/failure messages

Functions that currently take no reporter get an `Optional[WorkReporter] = None` parameter to stay backward-compatible.

## 3. Replace bare print() calls

All ~20 `print()` calls in the work path get replaced with the appropriate reporter method. Mapping:

| Current print | Reporter method |
|---|---|
| `"Plan {id} already completed"` | `reporter.info(...)` |
| `"Plan {id} has no chunks"` | `reporter.warning(...)` |
| `"Plan {id} completed (N chunks, N tasks)"` | `reporter.plan_summary(...)` |
| `"Run {run_id}: completed"` | `reporter.completed(...)` |
| `"Run {run_id}: failed"` | `reporter.failed(...)` |
| `"Stopping plan work..."` | `reporter.warning(...)` |
| `"Created follow-up task {id}"` | `reporter.info(...)` |
| Preflight errors | `reporter.warning(...)` |

## 4. Title resolution

Some call sites only have artifact IDs. Where titles aren't already loaded, we read them from the artifact's frontmatter. Most places already have the `Artifact` object loaded so `art.metadata.get("title", "")` is sufficient.

## 5. Parallel task output

When `max_parallel_tasks > 1`, interleaved output could be confusing. The reporter's `_write()` method will use a threading lock (similar to the existing `post_hook_lock` pattern in `execution.py`) to serialize output lines.

## 6. Tests

- Unit tests for `WorkReporter` formatting (symbols, colors, indentation)
- Integration-style tests that mock the reporter and verify the right methods are called during plan/chunk/task work flows
- Capture stderr/stdout in existing work tests to check for regressions

# Key artifacts

- New file: `src/onward/reporter.py`
- Modified: `src/onward/cli_commands.py`, `src/onward/execution.py`
- New test file: `tests/test_reporter.py`

# Acceptance criteria

- `onward work PLAN-XXX` on a plan with 2+ chunks and 3+ tasks produces hierarchical, colored output showing every status transition with titles
- `onward work TASK-XXX` on a single task shows status transitions
- Failed tasks show `✗` with failure reason
- `pytest` passes with no regressions
- `WorkReporter` class has unit tests covering all output methods
- Output respects `NO_COLOR` env var (or non-tty detection)
