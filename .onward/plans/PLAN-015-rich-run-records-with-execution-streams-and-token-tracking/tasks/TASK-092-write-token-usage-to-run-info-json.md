---
id: "TASK-092"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-027"
project: ""
title: "Write token_usage to info-*.json in execution.py"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: ["TASK-090", "TASK-091"]
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:40:00Z"
---

# Context

`ExecutorResult.token_usage` is now populated (from ack or CLI parser). This task
ensures it gets persisted into `info-*.json` as part of the final run record write.

# Scope

- In `execution.py`, when updating `info-*.json` after the executor returns, include `token_usage` from `ExecutorResult` (may be `None`)
- Prefer ack-provided `token_usage` over CLI-parsed; if both are present, merge (ack takes priority for token counts, CLI provides model name if ack doesn't)
- Ensure `token_usage: null` is written (not omitted) when unavailable, for consistent schema

# Out of scope

- Aggregation or display (CHUNK-028)

# Files to inspect

- `src/onward/execution.py` — final `run_json` write / update logic

# Implementation notes

- Read existing JSON, update `token_usage` key, write back — don't overwrite unrelated fields
- `json.dumps(..., indent=2)` for human-readable output

# Acceptance criteria

- [ ] `info-*.json` always contains a `token_usage` key after a run (either dict or null)
- [ ] When `ExecutorResult.token_usage` is a dict, it is stored verbatim
- [ ] When `ExecutorResult.token_usage` is `None`, `"token_usage": null` is written
- [ ] Existing fields in `info-*.json` (status, started_at, etc.) are preserved on update

# Handoff notes

After this task, the full token pipeline is in place. CHUNK-028 surfaces the data in CLI output.
