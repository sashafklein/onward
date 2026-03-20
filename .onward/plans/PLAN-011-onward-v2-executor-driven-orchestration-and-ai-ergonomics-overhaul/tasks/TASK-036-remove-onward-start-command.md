---
id: "TASK-036"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-009"
project: ""
title: "Remove onward start command"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:03Z"
updated_at: "2026-03-20T16:01:03Z"
---

# Context

`onward start` is a vestigial command. The `in_progress` status is now machine-managed by `onward work`. Keeping `start` confuses AI agents: they call `start` then `work` (redundant, since `work` sets `in_progress`), or they call `start` without `work`, leaving artifacts stuck in `in_progress`. Removing it simplifies the model: `work` owns execution state transitions, `complete`/`cancel` are the only manual closers.

# Scope

- Remove the `start` subcommand from `build_parser()` in `cli.py`
- Remove `cmd_start` function from `cli_commands.py`
- Remove the `cmd_start` import from `cli.py`
- Remove the `"start"` action from `transition_status()` transitions dict in `artifacts.py`
- Remove the `"start"` branch from `_lifecycle_transition_error()` in `artifacts.py`
- Update `LIFECYCLE.md`: remove `start` from manual commands table, update quick reference table
- Update `AGENTS.md`: remove `onward start <ID>` from the loop and all references
- Search and update `docs/AI_OPERATOR.md`, `docs/WORK_HANDOFF.md` for any `start` references
- Remove/update tests that exercise `onward start`
- Keep the `in_progress` status itself — still set by `onward work`

# Out of scope

- Changing how `onward work` sets `in_progress` (no change needed)
- Adding a deprecation period — this is a clean removal
- Adding any replacement command

# Files to inspect

- `src/onward/cli.py` — `build_parser()` (lines ~131-134, the `start_parser` block), `cmd_start` import (line ~25)
- `src/onward/cli_commands.py` — `cmd_start` (line ~435), `_cmd_set_status` (shared, keep for `complete`/`cancel`)
- `src/onward/artifacts.py` — `transition_status()` (line ~188, `"start"` entry), `_lifecycle_transition_error()` (lines ~154-165)
- `docs/LIFECYCLE.md` — manual commands table, quick reference, decision section
- `AGENTS.md` — the loop section with `onward start <ID>`
- `docs/AI_OPERATOR.md` — may reference `start`
- `docs/WORK_HANDOFF.md` — may reference `start`
- `tests/test_cli_work.py` — tests using `start`

# Implementation notes

- `_cmd_set_status` is shared by `start`, `complete`, and `cancel`. After removing `start`, the function still serves `complete`/`cancel` — no structural change needed to `_cmd_set_status` itself.
- `transition_status` has `"start": {"open": "in_progress"}`. Remove the entire `"start"` key from the `transitions` dict.
- Search the entire codebase for the string `"start"` in transition/status contexts. Be careful not to remove `"start"` from unrelated contexts (e.g., `started_at` field names, run record fields).
- The `TASK_MARKER_LEGEND_EPILOG` in `cli.py` may reference `start` — check and update if needed.
- `AGENTS.md` has `onward start <ID> ← Optional: mark in_progress` in the loop — remove this line entirely.

# Acceptance criteria

- `onward start TASK-X` produces argument parser error (unrecognized command)
- `onward work TASK-X` still transitions `open` → `in_progress` → `completed`/`failed`
- `transition_status("open", "start")` raises ValueError
- No references to `onward start` as a command remain in docs (OK in historical/migration context)
- All existing tests pass after removing start-specific tests
- `onward doctor` still passes

# Handoff notes

- This is independent of TASK-034/035 (failed status / circuit breaker) and can land in any order within CHUNK-009.
- After this lands, `LIFECYCLE.md` should clearly state that `in_progress` is machine-managed by `onward work`.
- If external agent configs (like Cursor rules) reference `onward start`, they'll need updating — flag in a follow-up task if discovered.
