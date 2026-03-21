---
id: "TASK-096"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-028"
project: ""
title: "Tests: run directory layout, backward compat, streaming, git diff, and token parsing"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on:
- "TASK-085"
- "TASK-087"
- "TASK-089"
- "TASK-091"
- "TASK-092"
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:56:28Z"
---

# Context

This task covers the test surface for all implementation chunks in PLAN-015.

# Scope

Write tests (or extend existing test files) for:

1. **Directory layout** — `_prepare_task_run` creates `runs/TASK-XXX/info-<ts>.json`, `summary-<ts>.log`, `output-<ts>.log` paths
2. **Backward compat** — `collect_runs_for_target` finds legacy `RUN-*-TASK-XXX.json` files and returns them alongside new-layout records
3. **Streaming write** — `_tee_stream` with a mock `file_out` writes every line and flushes; lock prevents interleaving
4. **Git diff helpers** — `get_head_sha` and `compute_files_changed` using a tmp git repo fixture
5. **Token parsing** — `extract_token_usage` with sample Claude CLI stderr strings (both NDJSON and plain-text)
6. **End-to-end** — A retried task has multiple run triples in its directory, each independently readable

# Out of scope

- Performance/load testing
- Browser/UI tests

# Files to inspect

- `tests/` — existing test files and fixtures to extend or mirror
- `src/onward/execution.py`, `executor_builtin.py`, `util.py` — modules under test

# Implementation notes

- Use `tmp_path` (pytest fixture) for all filesystem tests
- Git diff tests: `subprocess.run(["git", "init"], ...)` + `git commit` in `tmp_path`
- Mock `subprocess.run` for unit tests that shouldn't touch real git

# Acceptance criteria

- [ ] All 6 test categories above have at least one passing test
- [ ] `pytest` passes with no regressions on existing tests
- [ ] Tests run without network access or real Claude CLI

# Handoff notes

This is the last task in PLAN-015. After it passes, the plan can be marked complete.
