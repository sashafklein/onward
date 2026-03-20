---
id: "TASK-026"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-004"
project: ""
title: "Document tree task markers and CLI legend"
status: "completed"
description: "Document (A)/(H) markers in help/docs"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:52Z"
updated_at: "2026-03-20T14:37:08Z"
---

# Context

PLAN-010 phase 2 **§5**: document **`(A)`** and **`(H)`** markers (and any similar) in **CLI help** and user docs so agents parse `report`/`tree` output correctly.

# Scope

- Add legend to `onward tree --help`, `onward report --help` (or shared epilog), plus README/INSTALLATION snippet.
- Explain agent vs human task markers and blocking hints.

# Out of scope

- Changing marker characters (unless TASK-025 requires).

# Files to inspect

- `src/onward/cli.py` (argparse help strings), `README.md`, `INSTALLATION.md`, `docs/CONTRIBUTION.md`

# Implementation notes

- Keep help width readable; one short table is enough.

# Acceptance criteria

- Help text and docs define `(A)`/`(H)`; spot-check against actual printer code.

# Handoff notes

- Shared epilog `TASK_MARKER_LEGEND_EPILOG` on `onward tree` / `onward report` (`RawDescriptionHelpFormatter`); aligned with `render_active_work_tree_lines` + `is_human_task` in `artifacts.py` and `[Blocking Human Tasks]` in `cmd_report`.
- README (Seeing What’s Happening), INSTALLATION (Phase 1), CONTRIBUTION (feature list) updated.
