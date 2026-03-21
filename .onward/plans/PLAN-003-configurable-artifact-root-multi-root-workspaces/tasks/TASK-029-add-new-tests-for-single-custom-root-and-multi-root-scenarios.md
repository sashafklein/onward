---
id: "TASK-029"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-008"
project: ""
title: "Add new tests for single custom root and multi-root scenarios"
status: "completed"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "m"
depends_on:
- "TASK-028"
files: []
acceptance: []
created_at: "2026-03-21T15:49:56Z"
updated_at: "2026-03-21T18:44:10Z"
run_count: 1
last_run_status: "completed"
---

# Context

TASK-028 ensures existing tests pass with the new code. This task adds new test coverage for the configurable-root functionality that didn't exist before.

# Scope

- Create `tests/test_multi_root.py` (new file).
- Test scenarios:
  - `onward init` with `root: nb` creates the `nb/` directory tree.
  - `onward init` with `roots: {a: .a, b: .b}` creates both directory trees.
  - `onward new plan` with `--project` in multi-root creates plan under the correct root.
  - Missing `--project` in multi-root without `default_project` produces an error.
  - `default_project` config causes commands to use that project without `--project`.
  - `onward report` without `--project` in multi-root shows combined report.
  - Template fallback: project-specific template overrides shared template.
  - Cross-root ID uniqueness: creating artifacts in alternating projects yields sequential IDs.
  - `onward doctor` with multi-root reports missing directories per project.
  - Config validation: both `root` and `roots` set produces an error.

# Out of scope

- Fixing existing test failures (TASK-028).
- Performance or stress testing.
- Sync multi-root tests (can be added with TASK-027).

# Files to inspect

- `tests/test_multi_root.py` (to be created)
- `tests/conftest.py` — shared fixtures for creating multi-root workspaces
- `tests/test_layout.py` — unit tests from TASK-014 (complements these integration tests)

# Implementation notes

- Most tests should use CLI subprocess calls (`onward init`, `onward new plan --project a`, etc.) to test end-to-end behavior.
- Create a `multi_root_workspace` fixture that sets up a tmp directory with `.onward.config.yaml` containing `roots` config.
- Some tests need filesystem setup (create plan files in specific roots) before running commands.
- Cross-root ID test: create plan in project A, then plan in project B, assert IDs are PLAN-001 and PLAN-002.

# Acceptance criteria

- All new tests pass with `pytest tests/test_multi_root.py`.
- Coverage includes: init, new plan, --project requirement, default_project, combined report, template fallback, ID uniqueness, doctor, config validation.
- Full test suite `pytest tests/` passes including both old and new tests.

# Handoff notes

- These tests serve as the acceptance test suite for the entire PLAN-003 feature.
- If any test reveals a bug, file a follow-up task rather than blocking this task.
