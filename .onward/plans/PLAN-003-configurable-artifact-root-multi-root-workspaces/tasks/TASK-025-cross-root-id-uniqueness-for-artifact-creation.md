---
id: "TASK-025"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-006"
project: ""
title: "Cross-root ID uniqueness for artifact creation"
status: "in_progress"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "s"
depends_on:
- "TASK-018"
files: []
acceptance: []
created_at: "2026-03-21T15:49:40Z"
updated_at: "2026-03-21T17:56:28Z"
run_count: 1
---

# Context

Artifact IDs (PLAN-001, TASK-012, etc.) must be globally unique across all project roots. If two projects independently assign IDs, they could collide. The ID counter must scan all roots before generating the next number.

# Scope

- Update the ID generation logic in `cmd_new_plan`, `cmd_new_chunk`, `cmd_new_task` (and `cmd_new_task_batch`) to scan all configured roots for existing artifact IDs.
- The next ID number should be `max(all existing IDs of that type across all roots) + 1`.
- In `artifacts.py`, if there's a helper that finds the next available ID, update it to accept a layout and scan all roots.
- Ensure `artifact_glob` in multi-root mode returns artifacts from all roots so the max-ID calculation is correct.

# Out of scope

- Changing the ID format or adding project prefixes to IDs.
- Cross-root dependency tracking.
- Migrating artifacts.py paths (TASK-018 — prerequisite, already done).

# Files to inspect

- `src/onward/cli_commands.py` — `cmd_new_plan`, `cmd_new_chunk`, `cmd_new_task`, `cmd_new_task_batch` — where next ID is computed
- `src/onward/artifacts.py` — `artifact_glob` or any ID-scanning helper

# Implementation notes

- Current logic likely does: glob plans dir, extract max plan number, add 1. In multi-root, it must glob ALL plan dirs.
- This is a correctness requirement: duplicate IDs would cause ambiguous references in `onward show TASK-012` and break the `depends_on` graph.
- The scan should be cheap — it's just a directory listing across a few roots, not parsing file contents.
- Consider a helper like `next_artifact_id(layout, artifact_type) -> int` that encapsulates the cross-root scan.

# Acceptance criteria

- Creating a PLAN in project A yields PLAN-001. Creating a PLAN in project B yields PLAN-002 (not PLAN-001).
- Same for CHUNK and TASK IDs — globally unique.
- Works correctly with any number of roots.
- Single-root mode is unaffected.

# Handoff notes

- This is a small but critical correctness task. Test it manually: create artifacts in alternating projects and verify IDs increment globally.
