---
id: "TASK-011"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-005"
project: ""
title: "Extract orchestration services from cli.py"
status: "in_progress"
description: "Move command policy into cohesive modules with explicit APIs"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:22Z"
updated_at: "2026-03-20T00:57:42Z"
---

# Context

PLAN-010 phase 3 §6: **`cli.py` stays parser/dispatch**; domain policy moves to service-style modules so maintainers change behavior without editing glue everywhere (plan “Key artifacts” / end state).

# Scope

- Identify cohesive command handlers (report, list, work orchestration, sync entrypoints, etc.) that embed policy.
- Extract to one or more modules (e.g. `services.py`, `commands/`, or extend existing `execution.py` / `artifacts.py` with clear public functions).
- Keep `main()` thin: parse args → call service.

# Out of scope

- Full package re-layout or every private import fixed (TASK-012); architecture tests (TASK-013).

# Files to inspect

- `src/onward/cli.py` (large), `execution.py`, `artifacts.py`, `sync.py`, `split.py`

# Implementation notes

- Mechanical extract first; preserve behavior and tests. Prefer incremental PR-sized slices if needed.

# Acceptance criteria

- Meaningful reduction of non-parsing logic in `cli.py`; existing tests pass; no user-visible regression.

# Handoff notes

- Command implementations live in **`src/onward/cli_commands.py`** (~840 lines); **`src/onward/cli.py`** is argparse `build_parser()` + `main()` only (~210 lines).
- Entry point unchanged: `onward` → `onward.cli:main`. Tests use `from onward import cli`.
- **TASK-012** can treat `cli_commands` as the primary handler surface for stable public APIs over time.
