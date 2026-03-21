---
id: "TASK-042"
type: "task"
plan: "PLAN-005"
chunk: "CHUNK-013"
project: ""
title: "Fix regressions in existing tests from print-to-reporter migration"
status: "open"
description: ""
human: false
model: "sonnet"
executor: "onward-exec"
depends_on: ["TASK-038", "TASK-039", "TASK-040"]
files: []
acceptance: []
created_at: "2026-03-21T16:27:01Z"
updated_at: "2026-03-21T16:27:01Z"
---

# Context

After replacing all `print()` calls with reporter methods, some existing tests may assert on stdout content that has changed. This task finds and fixes those regressions.

# Scope

- Run `pytest` full suite and identify failures related to changed stdout output
- Update assertions in existing tests to match new reporter output format
- Verify no other regressions from the signature changes (added reporter parameter)

# Out of scope

- Writing new reporter-specific tests (TASK-041)
- Changing the reporter's output format to match old tests (the new format is correct)

# Files to inspect

- `tests/` — all test files, especially any that capture stdout during `work` command execution
- `tests/test_execution.py` if it exists
- `tests/test_cli.py` if it exists

# Implementation notes

- The main risk is tests that use `capsys` or redirect stdout and assert on specific print output like "Run {id}: completed"
- The new output will have different format (symbols, titles, indentation)
- Some tests may mock `print` — those will need to mock reporter methods instead
- If no tests actually assert on work-path stdout, this task may be trivially complete

# Acceptance criteria

- [ ] `pytest` full suite passes with 0 failures
- [ ] No test is skipped or disabled to work around the migration

# Handoff notes

Once this passes, PLAN-005 is complete.
