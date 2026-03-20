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

PLAN-010 problem: run snapshots used `.json` extension with non-JSON content. Acceptance: **`.json` files are valid JSON** on write.

# Scope

- Serialize new run records with strict JSON; keep a single write helper.
- Ensure all writers use it.

# Out of scope

- Removing legacy YAML-shaped read path (TASK-007).

# Files to inspect

- `src/onward/execution.py`, `src/onward/util.py`, `src/onward/artifacts.py`, `docs/WORK_HANDOFF.md`, `tests/test_run_record_io.py`

# Implementation notes

- UTF-8, deterministic formatting as already chosen (`ensure_ascii=False`, etc.).

# Acceptance criteria

- New `RUN-*.json` files parse as JSON; tests cover write path; handoff doc updated.

# Handoff notes

- `RUN-*.json` under `.onward/runs/` is written with strict JSON (`json.dumps`, UTF-8, `ensure_ascii=False`).
- Readers use `_read_run_json_record()` in `util.py` (JSON first, then legacy simple-YAML-shaped content).
- `docs/WORK_HANDOFF.md` updated. **TASK-007** can document migration if we ever drop YAML fallback.
