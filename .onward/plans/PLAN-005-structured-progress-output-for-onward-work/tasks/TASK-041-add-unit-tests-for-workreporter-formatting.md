---
id: "TASK-041"
type: "task"
plan: "PLAN-005"
chunk: "CHUNK-013"
project: ""
title: "Add unit tests for WorkReporter formatting"
status: "open"
description: ""
human: false
model: "sonnet-4-6"
executor: "onward-exec"
depends_on: ["TASK-037"]
files: ["tests/test_reporter.py"]
acceptance: []
created_at: "2026-03-21T16:26:57Z"
updated_at: "2026-03-21T16:26:57Z"
---

# Context

Add comprehensive tests for the `WorkReporter` class to validate all output methods, formatting, indentation, color handling, and thread safety.

# Scope

- Create `tests/test_reporter.py`
- Test each output method produces correct format (symbol, ID, title, status)
- Test indentation context manager (0, 1, 2 levels deep)
- Test color=False produces no ANSI codes
- Test NO_COLOR env var is respected
- Test thread safety: concurrent writes don't interleave mid-line
- Test plan_summary pluralization ("1 chunk" vs "2 chunks")
- Test edge cases: empty title, long title, special characters in title

# Out of scope

- Integration tests for the full work command path
- Testing the actual cli_commands / execution wiring

# Files to inspect

- `src/onward/reporter.py` — the class under test
- `tests/` — existing test patterns for style reference

# Implementation notes

- Use `io.StringIO` or `capsys` (pytest) to capture output
- For thread safety test: spawn N threads calling reporter methods concurrently, verify no garbled lines
- Construct `WorkReporter(color=False)` for most tests to avoid ANSI code matching complexity
- Test with color=True for a few cases to verify ANSI codes are present

# Acceptance criteria

- [ ] `tests/test_reporter.py` exists with 10+ test cases
- [ ] All WorkReporter methods covered
- [ ] Indentation tested at multiple levels
- [ ] Color on/off tested
- [ ] `pytest tests/test_reporter.py` passes

# Handoff notes

TASK-042 handles any regressions in existing tests from the print→reporter migration.
