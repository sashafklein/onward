---
id: "TASK-014"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-003"
project: ""
title: "Unit tests for WorkspaceLayout"
status: "open"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "m"
depends_on: ["TASK-012", "TASK-013"]
files: []
acceptance: []
created_at: "2026-03-21T15:49:14Z"
updated_at: "2026-03-21T15:49:14Z"
---

# Context

The WorkspaceLayout class and config validation from TASK-012/TASK-013 must be validated in isolation before any module migration begins. This ensures the path-resolution foundation is solid.

# Scope

- Create `tests/test_layout.py` (or add to `tests/test_config.py` if appropriate).
- Test `WorkspaceLayout.from_config` with:
  - Default config (no `root`/`roots`) — all paths resolve under `.onward`.
  - Single custom root (`root: nb`) — all paths resolve under `nb/`.
  - Multi-root (`roots: {a: .a-plans, b: .b-plans}`) — paths resolve per project key.
  - `default_project` fallback — `project=None` resolves to default in multi-root.
- Test each directory method returns the correct subdirectory path.
- Test `is_multi_root` property for all three modes.
- Test `all_project_keys()` returns correct keys.
- Test error cases:
  - Multi-root with no `default_project` and `project=None` raises `ValueError`.
  - Invalid project key raises `ValueError`.
- Test config validation:
  - Both `root` and `roots` set produces an error.
  - `default_project` not in `roots` keys produces an error.
  - Empty `root` value produces an error.
  - Empty `roots` mapping produces an error.

# Out of scope

- Integration tests with actual CLI commands (TASK-029).
- Testing scaffold or init behavior.

# Files to inspect

- `src/onward/config.py` (or `src/onward/layout.py`) — the WorkspaceLayout implementation
- `tests/test_config.py` — existing config test patterns to follow

# Implementation notes

- Use `tmp_path` fixture to create realistic workspace roots for path assertions.
- Keep tests pure unit tests — no subprocess calls or CLI invocations.
- Assert on `Path` objects, not strings, for cross-platform safety.
- Group tests by scenario (default, single-root, multi-root) using test classes or clear naming prefixes.

# Acceptance criteria

- All tests pass with `pytest tests/test_layout.py` (or the chosen file).
- Every public method on `WorkspaceLayout` has at least one test.
- Both happy-path and error-path cases are covered.
- No tests depend on the filesystem existing (use `tmp_path` or mock paths).

# Handoff notes

- If tests reveal design issues in WorkspaceLayout, fix in TASK-012 first and re-run.
- These tests will serve as the regression baseline for all migration tasks (TASK-018 through TASK-021).
