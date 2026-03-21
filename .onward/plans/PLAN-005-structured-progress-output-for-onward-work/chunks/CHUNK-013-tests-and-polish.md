---
id: "CHUNK-013"
type: "chunk"
plan: "PLAN-005"
project: ""
title: "Tests and polish"
status: "in_progress"
description: ""
priority: "medium"
model: "opus"
created_at: "2026-03-21T16:25:59Z"
updated_at: "2026-03-21T19:25:24Z"
---

# Summary

Add test coverage for the reporter and the wired-up work path, and polish any rough edges in the output formatting.

# Scope

- Unit tests for `WorkReporter` formatting (symbols, colors, indentation, thread safety)
- Integration tests verifying reporter methods are called during plan/chunk/task work flows
- Update any existing tests whose stdout assertions broke from the print→reporter migration
- Polish: verify edge case output (empty plans, all-completed, failures, parallel tasks)

# Out of scope

- Rich TUI features
- JSON output mode

# Dependencies

- CHUNK-011 (WorkReporter class)
- CHUNK-012 (wiring complete)

# Expected files/systems involved

- `tests/test_reporter.py` (new)
- `tests/test_execution.py` or other existing test files (updates)

# Completion criteria

- [ ] `pytest` passes with no regressions
- [ ] `WorkReporter` has unit tests covering all output methods
- [ ] At least one integration test exercises the full plan→chunk→task reporter output
- [ ] Edge cases tested: empty plan, already-completed, failure, skip
