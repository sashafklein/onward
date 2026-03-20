---
id: "TASK-020"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-007"
project: ""
title: "Implement execution success contract"
status: "open"
description: "Require verifiable task-acknowledged completion instead of generic zero exit"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:46Z"
updated_at: "2026-03-20T00:28:46Z"
---

# Context

PLAN-010 **§5d** + acceptance **execution truthfulness**: `onward work` must not mark tasks **completed** on generic **exit 0** alone — require **task-level success proof** (e.g. structured acknowledgment / result in executor output or extended payload contract).

# Scope

- Define success contract (schema or protocol) between Onward and executor; document in WORK_HANDOFF / schema docs.
- Parse executor stdout/stderr or agreed side-channel; fail run (task stays `open`) when proof missing.
- Persist evidence in run artifacts for auditing.

# Out of scope

- Replacing Ralph entirely; multi-provider routing (TASK-018/021) beyond what’s needed for the contract.

# Files to inspect

- `src/onward/execution.py`, `executor_payload.py`, `docs/WORK_HANDOFF.md`, `docs/schemas/`, `tests/test_cli_work.py`

# Implementation notes

- Plan suggests staging behind config if breaking; default can start as opt-in strict mode.

# Acceptance criteria

- Tests prove exit 0 without proof does **not** complete task; happy path with proof does.

# Handoff notes

<!-- Fill when closing. -->
