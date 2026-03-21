---
id: "TASK-028"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-008"
project: ""
title: "Update existing tests to use layout-aware path construction"
status: "completed"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "l"
depends_on: []
files: []
acceptance: []
created_at: "2026-03-21T15:49:55Z"
updated_at: "2026-03-21T18:35:44Z"
run_count: 1
last_run_status: "completed"
---

# Context

Many test files hardcode `tmp_path / ".onward/plans"` and similar paths. After the source modules are migrated to use `WorkspaceLayout`, tests must be updated to match the new function signatures and path construction patterns.

# Scope

- Create a shared test fixture (e.g. `make_default_layout(tmp_path)`) that returns a `WorkspaceLayout` with default `.onward` root for use in existing tests.
- Update all tests that call functions whose signatures changed (now accepting `layout` instead of or in addition to `root`).
- Update test helper functions that construct `.onward/` paths to use the layout fixture.
- Files to update:
  - `tests/test_cli_split.py`
  - `tests/test_cli_work.py`
  - `tests/test_cli_note.py`
  - `tests/test_cli_review.py`
  - `tests/test_cli_scale.py`
  - `tests/test_cli_lifecycle.py`
  - `tests/test_plan015_run_records.py`
  - `tests/test_run_record_io.py`
  - `tests/test_sync.py`
  - `tests/test_claimed_task_ids.py`
  - `tests/test_onboarding_simulation.py`
  - `tests/test_architecture_seams.py`
  - Any other test files with `.onward/` path construction

# Out of scope

- New tests for multi-root scenarios (TASK-029).
- Changing test behavior or coverage — only updating for API compatibility.

# Files to inspect

- All files in `tests/` — grep for `.onward` to find path references
- `tests/conftest.py` — existing shared fixtures

# Implementation notes

- The goal is that all existing tests pass with the migrated source code. No new test scenarios are added here.
- The shared fixture should be in `conftest.py` so all test files can use it.
- Some tests use CLI subprocess calls (`onward init`, `onward work`, etc.) — these may not need signature changes but may need config file setup to work with the layout.
- Tests that directly call `artifacts.py` or `execution.py` functions will need updated call sites.
- Start by running the full test suite and fixing failures one by one.

# Acceptance criteria

- `pytest tests/` passes with zero failures.
- No tests are skipped or deleted — all existing tests are updated to work.
- A shared `make_default_layout` (or similar) fixture exists in conftest.py.

# Handoff notes

- This task can be done incrementally alongside the migration tasks (018-021) — as each module is migrated, update its tests. But final verification needs all migrations done.
- TASK-029 adds new multi-root tests after this stabilization pass.
