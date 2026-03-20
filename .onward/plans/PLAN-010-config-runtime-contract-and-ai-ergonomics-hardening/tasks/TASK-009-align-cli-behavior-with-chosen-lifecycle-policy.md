---
id: "TASK-009"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-004"
project: ""
title: "Align CLI behavior with chosen lifecycle policy"
status: "completed"
description: "Make start/complete/cancel/work semantics consistent and testable"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:22Z"
updated_at: "2026-03-20T00:54:51Z"
---

# Context

PLAN-010 phase 2 step 4 (implementation half): **`docs/LIFECYCLE.md`** is canonical; CLI errors, edge cases, and tests must match **work-owned execution + manual overlays** (TASK-008).

# Scope

- Audit `start` / `complete` / `cancel` / `work` paths for mismatches vs LIFECYCLE (messages, invalid transitions, chunk failure leaves chunk `in_progress`, etc.).
- Add tests for invalid transitions and happy paths called out in LIFECYCLE.
- Tighten validation only where the doc promises it (avoid scope creep into TASK-024/027).

# Out of scope

- Rewriting all user-facing docs (TASK-010); provider/execution truthfulness (CHUNK-007).

# Files to inspect

- `src/onward/cli.py`, `src/onward/artifacts.py`, `src/onward/execution.py`, `docs/LIFECYCLE.md`, `tests/test_cli_*.py`

# Implementation notes

- Prefer clear `ValueError` / exit codes and user-visible strings that cite the policy (optional: “see docs/LIFECYCLE.md”).

# Acceptance criteria

- Tests cover invalid `complete` from `completed`, optional paths for `work` from `open` without prior `start`, and other rules in LIFECYCLE.
- No behavior contradicts LIFECYCLE without updating LIFECYCLE in the same change.

# Handoff notes

- `_lifecycle_transition_error()` in `artifacts.py` — actionable messages for invalid `start` / `complete` / `cancel` (references `docs/LIFECYCLE.md`).
- `_work_task()` in `execution.py` — clear error for `canceled` (and other non-runnable states).
- `cmd_work` — after chunk task failure, prints hint that chunk usually stays `in_progress` + LIFECYCLE link.
- Tests: `tests/test_cli_lifecycle.py` (invalid transitions, `work` without `start`, chunk failure hint).
- `docs/LIFECYCLE.md` intro/follow-up tweaked to match shipped behavior.
