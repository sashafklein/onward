---
id: "PLAN-013"
type: "plan"
project: ""
title: "Task claiming for chunk and plan execution"
status: "completed"
description: "Make tasks owned by an active chunk/plan work run invisible to other agents via a claiming mechanism"
priority: "medium"
model: "opus-latest"
created_at: "2026-03-21T00:21:29Z"
updated_at: "2026-03-21T03:18:01Z"
---

# Summary

When `onward work CHUNK-*` (or `PLAN-*`) is invoked, Onward serially executes every
child task. But during that execution, `onward report` and `onward next` still surface
those child tasks as available work — which is misleading if another agent or session
is looking for something to pick up. This plan introduces a **claiming** mechanism so
that tasks being worked through a parent execution are marked as claimed and hidden
from the "available work" surfaces.

# Problem

Today, when an agent runs `onward work CHUNK-005`, the chunk's child tasks (TASK-020
through TASK-025) remain status `open` or `in_progress` individually. A second agent
running `onward next` or `onward report` will see those tasks as available, potentially
starting duplicate work or creating confusion about what's actually spoken for.

There is no concept of "this group of tasks is currently being handled by a running
execution" — the only signal is the individual task's `in_progress` status, which is
set one-at-a-time as the executor reaches each task.

# Goals

- Tasks owned by an active `onward work CHUNK-*` or `onward work PLAN-*` run should
  not appear as actionable in `onward report`, `onward next`, or `onward show`
- Claiming should be lightweight — ideally computed from existing data rather than
  requiring per-task writes
- Abandoning a run (Ctrl-C, crash, stale ongoing.json) should release the claim so
  tasks don't get stuck as invisible forever
- The mechanism should compose with future parallelism (PLAN-014) where multiple
  chunks could be claimed simultaneously

# Non-goals

- Per-task claiming by individual humans ("I'm working on TASK-020") — that's a
  separate assignment feature
- Distributed locking across machines — `ongoing.json` is single-machine today
- Changing the status lifecycle (no new `claimed` status value in frontmatter)

# End state

- [ ] `onward work CHUNK-*` registers the chunk as claimed in `ongoing.json` before
  the task loop begins
- [ ] `onward work PLAN-*` registers each chunk as claimed as it enters execution
- [ ] `onward report` shows claimed tasks as `claimed` (dimmed) or omits them from
  the actionable sections, with a separate `[Claimed]` section
- [ ] `onward next` skips tasks whose parent chunk/plan is claimed
- [ ] `onward show TASK-*` displays "claimed by RUN-..." when applicable
- [ ] If a run finishes (success or failure), the claim is released
- [ ] If `ongoing.json` has a stale entry (process dead), a staleness heuristic
  releases the claim (e.g., PID check or configurable timeout)

# Context

The existing `ongoing.json` already tracks active runs with `id`, `target`, `status`,
`model`, `log_path`, and `started_at`. This is the natural place to record claims.
The key design question is whether claiming is **stored per-task** (write `claimed_by`
into each task's frontmatter) or **computed from the parent** (look up the chunk/plan
in `ongoing.json` and infer that its children are claimed).

The computed approach is preferred: it avoids N writes when a chunk starts, avoids
the risk of orphaned `claimed_by` fields if the process crashes between writes, and
keeps the task frontmatter clean. The trade-off is that report/next must cross-reference
`ongoing.json`, but that file is small and already loaded by the execution path.

# Proposed approach

## 1. Extend `ongoing.json` with claim scope

When `work_chunk` starts, before the task loop, write an entry like:

```json
{
  "id": "RUN-2026-03-21T00-30-00Z-CHUNK-005",
  "target": "CHUNK-005",
  "scope": "chunk",
  "claimed_children": ["TASK-020", "TASK-021", "TASK-022", ...],
  "pid": 12345,
  "status": "running",
  "started_at": "2026-03-21T00:30:00Z"
}
```

For plan-level work, one entry per chunk as it enters execution (or a single plan-level
entry with all chunk IDs + their task IDs). The `claimed_children` list is populated
by collecting open tasks in the chunk at claim time.

Adding `pid` enables staleness detection: if the process is no longer alive, the claim
can be released.

## 2. Claiming helper in `execution.py`

```python
def claimed_task_ids(root: Path) -> set[str]:
    """Return task IDs currently claimed by active runs (live PID check)."""
```

This function loads `ongoing.json`, filters to entries with `scope` in
`{"chunk", "plan"}`, checks each entry's PID (if present) to prune stale claims,
and returns the union of all `claimed_children` sets.

## 3. Wire claiming into `work_chunk` and `_work_plan`

- `work_chunk`: after `run_pre_chunk_shell_hooks`, before the task loop, register
  the claim entry. On exit (success, failure, or exception via try/finally), remove it.
- `_work_plan`: register each chunk's claim as it enters the chunk loop.

## 4. Update report / next / show

- `report_rows` and `select_next_artifact`: accept an optional `claimed_ids: set[str]`
  parameter. Tasks in that set get filtered into a `[Claimed]` section (report) or
  skipped entirely (next).
- `cmd_report`: call `claimed_task_ids(root)` and pass to report rendering.
- `cmd_next`: call `claimed_task_ids(root)` and exclude from selection.
- `cmd_show`: if the task is claimed, display "Claimed by RUN-..." with the parent
  run info.

## 5. Stale claim cleanup

`claimed_task_ids` performs a PID liveness check (`os.kill(pid, 0)` on Unix). If the
PID is dead, the entry is removed from `ongoing.json` on read. A configurable
`work.claim_timeout_minutes` (default: 120) also expires claims older than the
threshold regardless of PID check, as a safety valve.

## 6. Tests

- Unit: `claimed_task_ids` returns correct IDs; stale PID pruning works; empty
  `ongoing.json` returns empty set
- Integration: `work_chunk` registers and releases claims; report/next exclude
  claimed tasks; Ctrl-C (SIGINT) releases claim
- Edge: crash leaves stale claim → next report auto-cleans it

# Key artifacts

- `src/onward/execution.py` — claim registration, `claimed_task_ids()`
- `src/onward/cli_commands.py` — `cmd_report`, `cmd_next`, `cmd_show` integration
- `src/onward/artifacts.py` — `report_rows`, `select_next_artifact` filtering
- `.onward/ongoing.json` — extended schema with `scope`, `claimed_children`, `pid`

# Acceptance criteria

- `onward work CHUNK-*` in one terminal → `onward report` in another terminal shows
  the chunk's tasks as `claimed`, not as actionable
- `onward next` does not select a claimed task
- Killing the `onward work` process → next `onward report` releases the stale claim
- `work.claim_timeout_minutes: 0` disables claiming (all tasks always visible)
- Existing tests pass; new tests cover claiming lifecycle

# Notes

- This plan is intentionally independent of PLAN-014 (parallelism). Claiming works
  whether tasks are executed serially or in parallel — it's about visibility, not
  scheduling.
- The "computed from parent" approach means no migration is needed for existing task
  files.
- Future work: a `onward claim TASK-*` command for manual human claiming could build
  on this infrastructure but is out of scope here.
