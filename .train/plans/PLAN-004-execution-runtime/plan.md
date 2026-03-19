---
id: PLAN-004
type: plan
title: Execution runtime, task handoff, and parent-agent oversight
status: open
description: Implement run lifecycle management and file-backed orchestration at `train work`
priority: high
model: gpt-5
created_at: 2026-03-19T00:00:00Z
updated_at: 2026-03-19T00:00:00Z
---

# Summary

Implement the `work` boundary where Trains hands tasks to AI executors and tracks outcomes.

# Problem

There is no durable runtime state to coordinate, monitor, and recover work execution.

# Goals

- Implement `train work TASK-###` with run records and hook execution.
- Implement sequential `train work CHUNK-###` with dependency ordering.
- Persist runtime state under `.train/` for parent-agent visibility.
- Ensure workers can capture discovered follow-up tasks during execution.

# Non-goals

- Distributed queueing.
- Event-bus or daemon-first architecture.

# Context

v1 should stay simple: file-backed coordinator, synchronous executor invocation, deterministic status updates.

# Proposed approach

Create a run manager that writes `.train/ongoing.json`, emits immutable run snapshots, and streams logs while invoking the executor bridge.

# Risks

- Partial updates if process exits unexpectedly.
- Ambiguous resume behavior after failures.

# Chunking strategy

1. Run model + runtime file contracts.
2. Task execution lifecycle (`queued` -> `running` -> terminal state).
3. Chunk executor loop with stop/continue policy and hooks.

# Acceptance criteria

- `train work TASK-###` creates run metadata, streams output to `.train/runs/`, and updates task status on completion.
- `train work CHUNK-###` executes open tasks sequentially and respects dependency fields.
- `.train/ongoing.json` always reflects active runs and is valid JSON.
- Failed runs preserve logs and terminal metadata (`failed` with reason).
- `train progress` surfaces active run state from runtime files.
- Default worker guidance/hook path captures blocker/refactor/follow-up tasks with `blocked_by`, `human`, and `project` fields when available.

# Notes

See `docs/architecture/work-handoff.md` for handoff design decisions.
