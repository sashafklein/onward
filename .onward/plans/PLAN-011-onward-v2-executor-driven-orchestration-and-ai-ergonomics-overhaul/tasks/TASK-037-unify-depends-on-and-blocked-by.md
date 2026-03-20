---
id: "TASK-037"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-009"
project: ""
title: "Unify depends_on and blocked_by"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:03Z"
updated_at: "2026-03-20T16:01:03Z"
---

# Context

Onward has two dependency fields: `depends_on` (checks if dependency is `completed`) and `blocked_by` (blocks unconditionally regardless of status). This dual mechanism is a trap for AI agents — they use one when they mean the other, or use both inconsistently. This task unifies them: `depends_on` becomes the single mechanism, and `blocked_by` becomes a deprecated read-compat alias that maps to `depends_on` semantics.

# Scope

- In `task_is_next_actionable()` in `artifacts.py`: merge `blocked_by` entries into `depends_on` for evaluation. Replace the current pattern (unconditional block for `blocked_by`, completion-check for `depends_on`) with unified completion-based checking of both fields.
- In `blocking_ids()` in `artifacts.py`: continue reading both fields for backward compat, add deprecation comment for `blocked_by`.
- Update `cmd_new_task()` in `cli_commands.py`: stop emitting `blocked_by` in new task metadata. Only emit `depends_on`.
- Update `prepare_task_writes()` in `split.py`: stop emitting `blocked_by` in generated tasks.
- Add a deprecation warning in `onward doctor` (in `cli_commands.py` `cmd_doctor`) when any artifact uses `blocked_by` — suggest migration to `depends_on`.
- Update `LIFECYCLE.md` to document `depends_on` as the single dependency mechanism.
- Update task template in `scaffold.py` `DEFAULT_FILES` to remove `blocked_by` from the default metadata fields.
- Do NOT remove `blocked_by` from parsing — existing artifacts with `blocked_by` must still work.

# Out of scope

- Automated migration script to rewrite existing `blocked_by` → `depends_on` in files
- Removing `blocked_by` from the YAML parser entirely (keep read compat indefinitely)
- Changing chunk-level dependency semantics
- Adding any new dependency types (e.g., soft dependencies)

# Files to inspect

- `src/onward/artifacts.py` — `task_is_next_actionable()` (lines ~232-247), `blocking_ids()` (lines ~221-229), `select_next_artifact()`
- `src/onward/cli_commands.py` — `cmd_new_task()` metadata dict (line ~279), `cmd_doctor()` for deprecation warning
- `src/onward/split.py` — `prepare_task_writes()` metadata dict (line ~230)
- `src/onward/scaffold.py` — `DEFAULT_FILES` task template metadata
- `src/onward/execution.py` — `ordered_ready_chunk_tasks()` (line ~398) reads `depends_on`
- `docs/LIFECYCLE.md` — dependency documentation

# Implementation notes

- The key change in `task_is_next_actionable()` replaces:
  ```python
  if as_str_list(artifact.metadata.get("blocked_by")):
      return False  # unconditional block
  depends_on = as_str_list(artifact.metadata.get("depends_on"))
  unmet = [dep for dep in depends_on if status_by_id.get(dep) != "completed"]
  ```
  with:
  ```python
  all_deps = (
      as_str_list(artifact.metadata.get("depends_on"))
      + as_str_list(artifact.metadata.get("blocked_by"))
  )
  unmet = [dep for dep in all_deps if status_by_id.get(dep) != "completed"]
  ```
- `blocking_ids()` already reads both fields — just needs a comment that `blocked_by` is deprecated.
- For the `onward doctor` warning: add a non-fatal warning (not a failing issue) when any artifact has a non-empty `blocked_by` list. Pattern: `"warning: {path}: 'blocked_by' is deprecated, use 'depends_on' instead"`.
- `ordered_ready_chunk_tasks()` in `execution.py` reads `depends_on` — verify it also handles the merged `blocked_by` entries after this change (it calls into `task_is_next_actionable` indirectly via the same logic pattern — check if it duplicates the dep check).

# Acceptance criteria

- New tasks from `onward new task` only have `depends_on` (no `blocked_by` in metadata)
- Tasks from `onward split` only have `depends_on` (no `blocked_by`)
- Existing tasks with `blocked_by: ["TASK-X"]` behave as `depends_on: ["TASK-X"]` (unblocked when TASK-X completes)
- `onward doctor` warns about `blocked_by` usage in existing artifacts
- `docs/LIFECYCLE.md` documents `depends_on` as the single mechanism
- Task template in scaffold doesn't include `blocked_by`
- All existing tests pass
- New test: a task with only `blocked_by: ["TASK-X"]` becomes actionable when TASK-X is completed

# Handoff notes

- This is backward-compatible: old artifacts with `blocked_by` still work, just with completion-based semantics instead of unconditional blocking.
- A future task could add `onward migrate` that rewrites `blocked_by` → `depends_on` in existing files.
- The existing PLAN-010 tasks use `blocked_by` for unconditional blocking. After this change, they'll be completion-based — which is actually the correct intended behavior.
- This task is independent of TASK-034/035/036 and can land in any order within CHUNK-009.
