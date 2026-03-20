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

- `schema_version: 1` is set on all executor stdin payloads (task, review, hook) via `with_schema_version()` in `executor_payload.py`.
- `validate_executor_stdin_payload()` is for tests/tooling; JSON Schema lives at `docs/schemas/onward-executor-stdin-v1.schema.json`.
- Bump `EXECUTOR_PAYLOAD_SCHEMA_VERSION` and the schema file together when breaking stdin shape.
