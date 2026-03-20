---
id: "TASK-041"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-011"
project: ""
title: "Define and implement structured task result schema"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:06Z"
updated_at: "2026-03-20T16:01:06Z"
---

# Context

CHUNK-011 adds structured feedback from executor runs. Currently the executor can only report success/failure via exit code, plus an optional `onward_task_result` ack with minimal fields. This task defines and implements a richer structured result schema that lets the executor report files changed, follow-up work discovered, acceptance criteria met/unmet, and a human-readable summary. This data is stored on the run record and made available to downstream consumers.

# Scope

- Define v2 of the task result schema in `docs/schemas/onward-task-result-v2.schema.json` (JSON Schema)
- The result object shape:
  ```json
  {
    "onward_task_result": {
      "schema_version": 2,
      "status": "completed",
      "run_id": "RUN-...",
      "summary": "string",
      "files_changed": ["path", ...],
      "follow_ups": [{"title": "...", "description": "...", "priority": "low|medium|high"}],
      "acceptance_met": ["criterion text", ...],
      "acceptance_unmet": ["criterion text", ...],
      "notes": "optional free-text"
    }
  }
  ```
- Update `executor_ack.py` to validate v2 results (backward compat with v1)
- Update `_validate_ack_object` to handle `schema_version: 2` with the extended fields
- Store the full parsed result on the run record JSON in `_execute_task_run()` (already stores `success_ack` — extend it)
- Add `parse_task_result(obj)` function that extracts structured fields with defaults for missing optional fields
- Update `SUCCESS_ACK_SCHEMA_VERSION` to 2 (keep accepting v1 for backward compat)
- Add tests for v2 parsing, v1 backward compat, and edge cases (missing optional fields)

# Out of scope

- Auto-creating follow-up tasks from results (TASK-042)
- Displaying results in `onward show` (TASK-043)
- Modifying the executor to emit v2 results (that's the executor's responsibility)
- Changing the executor stdin payload schema

# Files to inspect

- `src/onward/executor_ack.py` — `_validate_ack_object`, `find_task_success_ack`, `SUCCESS_ACK_SCHEMA_VERSION`
- `src/onward/execution.py` — `_execute_task_run()` where `success_ack` is stored on the run record (line ~333)
- `docs/schemas/` — for the JSON schema file (new)
- `tests/test_executor_ack.py` — existing ack tests to extend

# Implementation notes

- Backward compat: when `schema_version` is 1 (or missing), validate with v1 rules (current behavior). When `schema_version` is 2, validate extended fields but treat most as optional.
- The `parse_task_result(obj)` function should normalize the result:
  - `files_changed`: default `[]`
  - `follow_ups`: default `[]`, each entry must have `title` and `description`
  - `acceptance_met`/`acceptance_unmet`: default `[]`
  - `summary`: default `""`
  - `notes`: default `""`
- The run record already stores `success_ack` as the raw JSON object. After this change, store both the raw ack and a normalized `task_result` key with the parsed/validated result.
- The JSON Schema file in `docs/schemas/` is documentation/reference — Onward doesn't do schema-based validation at runtime (it uses the Python validation in `executor_ack.py`).
- Keep `find_task_success_ack` return signature unchanged — it already returns `(found, err, obj)`. Callers can then pass `obj` to `parse_task_result` for the structured data.

# Acceptance criteria

- `docs/schemas/onward-task-result-v2.schema.json` exists with complete schema
- `executor_ack.py` validates v2 results with extended fields
- v1 results (no `files_changed`, etc.) still validate successfully
- `parse_task_result(obj)` returns normalized dict with all fields defaulted
- Run record JSON includes `task_result` with parsed data when available
- Tests cover: v2 parsing, v1 backward compat, missing optional fields, invalid follow-up entries

# Handoff notes

- TASK-042 and TASK-043 depend on this. They consume the `task_result` from run records.
- The executor reference script (`scripts/onward-exec`) should be updated to emit v2 results — but that's outside this task's scope (it's part of the executor chunk work).
- The `follow_ups` field is the key enabler for TASK-042 (auto-creating follow-up tasks).
