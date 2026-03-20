---
id: "TASK-006"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-003"
project: ""
title: "Define and version executor payload schema"
status: "completed"
description: "Publish machine-readable schema for task/review/hook payload contracts"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:21Z"
updated_at: "2026-03-20T00:44:51Z"
---

# Context

PLAN-010 acceptance: executor stdin for `work`, `review-plan`, and markdown hooks is **machine-safe and versioned**; integrators can validate payloads.

# Scope

- Add integer `schema_version` on all outbound stdin JSON (single current version, e.g. `1`).
- Publish JSON Schema (draft 2020-12) + tests that validate representative payloads.
- Document location of schema in `docs/schemas/` and WORK_HANDOFF.

# Out of scope

- Legacy reader behavior for old captures without `schema_version` (TASK-007).

# Files to inspect

- `src/onward/executor_payload.py`, `src/onward/execution.py`, `docs/schemas/onward-executor-stdin-v1.schema.json`, `docs/WORK_HANDOFF.md`, `tests/test_executor_payload.py`

# Implementation notes

- Bump `EXECUTOR_PAYLOAD_SCHEMA_VERSION` and schema file together when breaking shape.

# Acceptance criteria

- All executor stdin writes include `schema_version`; schema file checked in; tests pass.

# Handoff notes

- `schema_version: 1` is set on all executor stdin payloads (task, review, hook) via `with_schema_version()` in `executor_payload.py`.
- `validate_executor_stdin_payload()` is for tests/tooling; JSON Schema lives at `docs/schemas/onward-executor-stdin-v1.schema.json`.
- Bump `EXECUTOR_PAYLOAD_SCHEMA_VERSION` and the schema file together when breaking stdin shape.
