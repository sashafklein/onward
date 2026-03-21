---
id: "CHUNK-027"
type: "chunk"
plan: "PLAN-015"
project: ""
title: "Token usage tracking"
status: "completed"
description: ""
priority: "medium"
model: "sonnet-latest"
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:56:25Z"
---

# Summary

Adds optional token usage tracking to run records. The `info-*.json` gets a
`token_usage` field (nullable). Two collection paths are supported: parsing Claude
CLI output, and accepting `token_usage` from the executor's ack JSON. The system
degrades gracefully to `null` when usage data is unavailable.

# Scope

- Extend `info-*.json` schema with a nullable `token_usage` object (`input_tokens`, `output_tokens`, `total_tokens`, `model`)
- Add `token_usage` to `ExecutorResult` dataclass (`src/onward/executor.py`)
- Extend ack schema v3 in `executor_ack.py` with optional `token_usage` field
- Add `extract_token_usage(output: str) -> dict | None` in `executor_builtin.py` to parse Claude CLI stderr summary line
- Wire token usage into `info-*.json` final write in `execution.py`

# Out of scope

- Dollar-cost estimation (deferred per plan)
- Token usage for SubprocessExecutor (ack-based path covers it)
- Enforcing token usage presence (it's always best-effort / nullable)

# Dependencies

- CHUNK-024 (provides `info-*.json` path)

# Expected files/systems involved

- `src/onward/executor.py` — `ExecutorResult` dataclass
- `src/onward/executor_ack.py` — ack schema v3
- `src/onward/executor_builtin.py` — `extract_token_usage` parser
- `src/onward/execution.py` — writes token_usage to info JSON

# Completion criteria

- [ ] `info-*.json` has a `token_usage` key (null or populated) for every new run
- [ ] When Claude CLI provides usage data, `token_usage` is non-null
- [ ] Ack-provided `token_usage` is stored in preference to / merged with parsed output
- [ ] No crash or warning when usage data is absent

# Notes

Token extraction from Claude CLI is best-effort and may break across CLI versions. The regex should be narrow enough to fail silently rather than produce garbage.
