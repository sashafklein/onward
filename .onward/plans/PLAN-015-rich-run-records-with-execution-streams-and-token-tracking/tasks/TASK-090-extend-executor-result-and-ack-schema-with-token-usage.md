---
id: "TASK-090"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-027"
project: ""
title: "Extend ExecutorResult and ack schema v3 with token_usage"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on:
- "TASK-084"
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:56:23Z"
---

# Context

Token usage needs to flow from executor to run record. The cleanest path is the
existing `ExecutorResult` dataclass and the ack JSON schema. This task adds the
field to both so downstream consumers have a stable interface.

# Scope

- Add `token_usage: dict | None = None` to `ExecutorResult` in `src/onward/executor.py`
- Extend ack parsing in `src/onward/executor_ack.py` to read `token_usage` from the `onward_task_result` JSON and populate it on the returned result
- Bump ack `schema_version` to 3 (or validate existing versioning strategy)
- Document the new optional field in the ack schema docstring/comment

# Out of scope

- Actual token extraction from CLI output (TASK-091)
- Writing token_usage to info JSON (TASK-092)

# Files to inspect

- `src/onward/executor.py` — `ExecutorResult` dataclass
- `src/onward/executor_ack.py` — ack parsing logic and schema version

# Implementation notes

- `token_usage` dict shape: `{"input_tokens": int, "output_tokens": int, "total_tokens": int, "model": str}` — all fields optional within the dict
- Ack v3 is backward-compatible: old acks without `token_usage` parse to `None`

# Acceptance criteria

- [ ] `ExecutorResult.token_usage` field exists and defaults to `None`
- [ ] Ack JSON with `"token_usage": {...}` is parsed and stored on `ExecutorResult`
- [ ] Ack JSON without `token_usage` parses without error, leaving `None`
- [ ] Unit tests cover both cases

# Handoff notes

TASK-091 adds the Claude CLI parser that populates this field from the builtin executor path.
