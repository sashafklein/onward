---
id: "TASK-020"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-007"
project: ""
title: "Implement execution success contract"
status: "completed"
description: "Require verifiable task-acknowledged completion instead of generic zero exit"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:46Z"
updated_at: "2026-03-20T05:48:43Z"
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

- **`work.require_success_ack`** (default false) in config + scaffold; **`src/onward/executor_ack.py`** parses bottom-up JSON lines with **`onward_task_result`** (`status: completed`, `schema_version: 1`, optional **`run_id`** must match **`ONWARD_RUN_ID`** env set on the task subprocess).
- **`execution._execute_task_run`:** after exit 0, strict mode requires ack; **`success_ack`** stored on run JSON when a valid ack is parsed.
- Schema **`docs/schemas/onward-task-success-ack-v1.schema.json`**; docs: **WORK_HANDOFF**, **CAPABILITIES**, **FORMAT_MIGRATION**, **schemas/README**.
- Tests: **`tests/test_executor_ack.py`**, **`tests/test_cli_work.py`** (strict fail / strict pass with Python ack script), **`tests/test_architecture_seams.py`** (schema const).
