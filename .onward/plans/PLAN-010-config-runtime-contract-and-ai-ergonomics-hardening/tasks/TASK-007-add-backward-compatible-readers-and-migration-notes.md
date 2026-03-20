---
id: "TASK-007"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-003"
project: ""
title: "Add backward-compatible readers and migration notes"
status: "completed"
description: "Avoid breaking older run artifacts while normalizing formats"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:21Z"
updated_at: "2026-03-20T00:49:03Z"
---

# Context

PLAN-010 risk handling: **backward compatibility** while normalizing formats — older workspaces must keep working; migration policy documented.

# Scope

- Tolerant **readers** for run records (JSON first, legacy simple-YAML-shaped) and optional-field defaults on parse.
- **Executor stdin:** normalize/validate paths that treat missing/null `schema_version` as legacy v1 where appropriate.
- **`docs/FORMAT_MIGRATION.md`** + links from WORK_HANDOFF / schema README.

# Out of scope

- One-shot migration tool that rewrites all old run files on disk (policy only unless explicitly added).

# Files to inspect

- `src/onward/util.py`, `src/onward/executor_payload.py`, `docs/FORMAT_MIGRATION.md`, `tests/test_run_record_io.py`, `tests/test_executor_payload.py`

# Implementation notes

- Dropping YAML fallback = breaking major; document before removing.

# Acceptance criteria

- Tests cover legacy run shape + legacy stdin; migration doc committed; cross-links in place.

# Handoff notes

- `_read_run_json_record()` now returns records merged with `_RUN_RECORD_OPTIONAL_DEFAULTS` in `util.py` so sparse legacy snapshots get stable `type` / `plan` / `chunk` / `executor` / `error` / `finished_at`.
- `normalize_executor_stdin_payload()` in `executor_payload.py` fills missing or null `schema_version`; `validate_executor_stdin_payload()` uses the same defaulting for required-key checks while still rejecting wrong non-null versions.
- Migration doc: `docs/FORMAT_MIGRATION.md`; cross-links from `WORK_HANDOFF.md` and `docs/schemas/README.md`; schema `description` updated for legacy stdin.
- Tests: `tests/test_run_record_io.py` (sparse run record), `tests/test_executor_payload.py` (legacy stdin + normalize).
