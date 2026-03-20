---
id: "TASK-005"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-003"
project: ""
title: "Unify persisted run file formats"
status: "completed"
description: "Ensure file extension and serialization format match exactly"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:21Z"
updated_at: "2026-03-20T00:43:51Z"
---

# Context

<!-- What this task is doing and where it fits in the chunk. -->

# Scope

<!-- Tight, concrete bullets. Keep this task small and finishable. -->

# Out of scope

<!-- Explicitly exclude adjacent work. -->

# Files to inspect

<!-- Start here. Include exact paths when known. -->

# Implementation notes

<!-- Constraints, gotchas, and edge cases to handle. -->

# Acceptance criteria

<!-- Binary checks: tests, outputs, behavior changes, docs updates. -->

# Handoff notes

- `RUN-*.json` under `.onward/runs/` is written with strict JSON (`json.dumps`, UTF-8, `ensure_ascii=False`).
- Readers use `_read_run_json_record()` in `util.py` (JSON first, then legacy simple-YAML-shaped content).
- `docs/WORK_HANDOFF.md` updated. **TASK-007** can document migration if we ever drop YAML fallback.
