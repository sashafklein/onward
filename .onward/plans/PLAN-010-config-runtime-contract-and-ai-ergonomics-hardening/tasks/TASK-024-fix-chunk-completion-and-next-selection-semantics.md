---
id: "TASK-024"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-004"
project: ""
title: "Fix chunk completion and next selection semantics"
status: "open"
description: "Auto-complete chunks with no actionable tasks and prevent next from selecting dead chunks"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:52Z"
updated_at: "2026-03-20T00:28:52Z"
---

# Context

PLAN-010 phase 2 **§5** UX bugs: **chunk completion** when all child tasks are completed; **`onward next`** must not return **non-actionable** items (e.g. chunks that cannot be progressed without human steps).

# Scope

- Fix `_select_next_artifact` / chunk status rules so `next` surfaces actionable work; align chunk auto-completion with LIFECYCLE when all tasks terminal.
- Add regression tests for reported bad states.

# Out of scope

- Tree labeling (TASK-025/026); split dry-run labels (TASK-027).

# Files to inspect

- `src/onward/artifacts.py` (`_select_next_artifact`, index helpers), `src/onward/cli.py` (`cmd_next`), `src/onward/execution.py` (chunk work completion), `tests/`

# Implementation notes

- Cross-check `human`, `blocked_by`, `depends_on` when ranking “next”.

# Acceptance criteria

- Tests encode expected `next` behavior; chunk completion matches documented intent in LIFECYCLE/README.

# Handoff notes

<!-- Fill when closing. -->
