---
id: "PLAN-014"
type: "plan"
project: ""
title: "Dependency-aware parallel task execution"
status: "completed"
description: "Execute independent tasks within a chunk concurrently, respecting dependency edges and a configurable parallelism limit"
priority: "medium"
model: "opus-latest"
created_at: "2026-03-21T00:21:31Z"
updated_at: "2026-03-21T03:35:29Z"
---

# Summary

Onward currently executes tasks strictly serially, even when multiple tasks within a
chunk have no dependency relationship and could safely run simultaneously. This plan
adds a `work.max_parallel_tasks` config setting (default 1, preserving current
behavior), teaches the split prompts to produce meaningful `depends_on` edges, and
updates the executor loop to dispatch independent tasks in parallel up to the
configured limit.

# Problem

Serial execution is a bottleneck. A chunk with 6 independent tasks that each take
5 minutes costs 30 minutes wall-clock. With parallelism=3, that drops to ~10 minutes.
The infrastructure for dependency tracking (`depends_on`) already exists but is
underutilized — today it only gates ordering within the serial loop. The executor
architecture (`execute_batch`) already operates on lists of tasks, making parallel
dispatch a natural extension.

Additionally, the current split prompts don't explicitly instruct the AI to reason
about task independence vs. dependency. This leads to tasks that are implicitly
independent but not declared as such, and tasks that have real ordering constraints
but no `depends_on` edges.

# Goals

- Add `work.max_parallel_tasks` config key (integer, default 1)
- When > 1, dispatch up to N ready (unblocked) tasks concurrently within a chunk
- Ensure `depends_on` edges are respected: a task doesn't start until all its
  dependencies are `completed`
- Update split prompts to explicitly reason about task independence and mark
  `depends_on` where ordering matters
- Parallel tasks get independent run records, logs, and status updates
- Failure in one parallel task stops new dispatches but doesn't kill in-flight tasks

# Non-goals

- Cross-chunk parallelism (running multiple chunks of a plan at once) — future work
- Git worktree isolation per parallel task — significant complexity, deferred
- Distributed execution across machines
- Changing the `depends_on` schema (it already supports lists of IDs)

# End state

- [ ] `work.max_parallel_tasks: 3` in config → `onward work CHUNK-*` runs up to 3
  tasks concurrently
- [ ] Tasks with `depends_on` edges wait for their dependencies to complete
- [ ] `onward split CHUNK-*` produces tasks with explicit `depends_on` when order
  matters, and no `depends_on` when tasks are independent
- [ ] `onward report` shows all parallel in-flight tasks as `in_progress`
- [ ] A failing task causes the wave to drain (in-flight tasks finish, no new ones
  start) rather than hard-killing siblings
- [ ] `max_parallel_tasks: 1` (default) preserves exactly current serial behavior
- [ ] Run records are independent per task — no shared log files

# Context

**Current execution loop** (`work_chunk` in `execution.py`): iterates in a
`while True` loop, calling `ordered_ready_chunk_tasks()` to get ready tasks (those
whose `depends_on` are all `completed`), preparing a wave, and dispatching via
`_run_hooked_executor_batch()`. The batch iterator yields results one at a time.

When `work.sequential_by_default` is false (current non-sequential mode), only one
task per loop iteration is executed — it's not true parallelism, just "execute one
and re-check readiness."

**Executor architecture**: `Executor.execute_batch()` accepts a list of `TaskContext`
and yields `ExecutorResult` sequentially. `BuiltinExecutor` spawns one subprocess
per task. For true parallelism, we need either:
1. Concurrent `execute_task` calls (threading or asyncio), or
2. A new `execute_parallel` method that manages multiple subprocesses

Option 1 (threading) is simpler and sufficient since execution is I/O-bound
(waiting on subprocess). Each thread runs `execute_task` independently.

**Split prompts**: `.onward/prompts/split-chunk.md` instructs the AI to produce task
YAML. It should be updated to explicitly require dependency reasoning.

# Proposed approach

## Phase 1: Config and dependency infrastructure

### 1a. Add `work.max_parallel_tasks` config key

In `config.py`, add:

```python
def work_max_parallel_tasks(config: dict) -> int:
    work = config.get("work", {})
    val = work.get("max_parallel_tasks", 1)
    return max(1, int(val))
```

Document in `.onward.config.yaml` comments and `docs/CAPABILITIES.md`.

### 1b. Validate dependency graph at chunk execution time

Before dispatching, build a DAG from the chunk's tasks and their `depends_on` edges.
Detect cycles (error out) and validate that all referenced IDs exist within the chunk
or are already completed.

```python
def validate_chunk_dag(tasks: list[Artifact]) -> list[str]:
    """Return list of errors (empty = valid). Checks for cycles and dangling refs."""
```

## Phase 2: Parallel executor dispatch

### 2a. Thread-pool executor wrapper

Add a `parallel_execute` function that takes a list of `TaskContext` items and
`max_workers`, and uses `concurrent.futures.ThreadPoolExecutor` to run
`executor.execute_task()` for each:

```python
def parallel_execute(
    executor: Executor,
    root: Path,
    tasks: list[TaskContext],
    max_workers: int,
) -> list[ExecutorResult]:
```

Each task gets its own thread. Results are collected as futures complete. If any
task fails, no new tasks are submitted but in-flight tasks are allowed to finish.

### 2b. Update `work_chunk` loop

Replace the current "pick one wave, run it serially" with:

```
while ready tasks exist:
    ready = ordered_ready_chunk_tasks(...)
    eligible = filter(circuit_breaker_check, ready)
    batch = eligible[:max_parallel_tasks]
    results = parallel_execute(executor, root, batch, max_parallel_tasks)
    for result in results:
        finalize(result)  # write run record, update status
    if any_failed(results):
        drain and stop
```

When `max_parallel_tasks == 1`, this degrades to exactly the current serial behavior.

### 2c. Hook sequencing under parallelism

Pre-task and post-task shell hooks run per-task, within each task's thread. They are
not shared across parallel tasks. This matches the current contract where hooks receive
`ONWARD_TASK_ID` env vars specific to one task.

The `post_task_shell` hook (typically a git commit) needs care: parallel git commits
will conflict. Options:
- Document that `post_task_shell` git commits should use `--no-verify` and handle
  conflicts, or
- Serialize hook execution with a lock (preferred for correctness)
- Recommend disabling auto-commit hooks when `max_parallel_tasks > 1`

We'll implement hook serialization via a threading lock and document the interaction.

## Phase 3: Split prompt improvements

### 3a. Update `split-chunk.md` prompt

Add explicit instructions:

> For each task, evaluate whether it depends on the output or side-effects of any
> other task in the chunk. If so, add `depends_on: [TASK-ID]` to its frontmatter.
> If a task can be completed independently (no shared files, no sequential ordering
> requirement), omit `depends_on` to enable parallel execution.
>
> Common dependency patterns:
> - Writing a module → writing tests for that module (test depends on module)
> - Creating a schema → implementing code that uses the schema
> - Refactoring an interface → updating all callers
>
> Tasks that touch disjoint files or concepts are typically independent.

### 3b. Update `split-plan.md` prompt

Add similar guidance for chunk-level dependencies (though chunk parallelism is
future work, getting the edges right now helps).

### 3c. Validation in `validate_split_output`

Add a warning if a split produces > 3 tasks with zero `depends_on` edges and the
tasks appear to touch overlapping files (heuristic: shared path prefixes in task
descriptions). This helps catch under-specified dependencies.

## Phase 4: Reporting and observability

### 4a. `onward report` shows parallel runs

When multiple tasks are `in_progress` in the same chunk, group them under the chunk:

```
[In Progress]
  CHUNK-005  chunk  in_progress  Execution improvements
    TASK-020  task  in_progress  Add config key
    TASK-021  task  in_progress  Thread pool executor
    TASK-022  task  open         Update hooks (blocked by TASK-020)
```

### 4b. `onward show` displays dependency graph

For a chunk, show a simple text DAG:

```
TASK-020 (open)
├── TASK-021 (open, depends_on: TASK-020)
└── TASK-022 (open, depends_on: TASK-020)
TASK-023 (open, independent)
```

# Key artifacts

- `src/onward/config.py` — `work_max_parallel_tasks()`
- `src/onward/execution.py` — `parallel_execute()`, updated `work_chunk`, DAG validation
- `src/onward/executor.py` — potentially `execute_parallel()` on `Executor` ABC
- `.onward/prompts/split-chunk.md` — dependency reasoning instructions
- `.onward/prompts/split-plan.md` — chunk dependency instructions
- `docs/CAPABILITIES.md` — document `max_parallel_tasks` config
- `.onward.config.yaml` — add `max_parallel_tasks` key with default

# Acceptance criteria

- `max_parallel_tasks: 1` (default) → identical serial behavior, all existing tests pass
- `max_parallel_tasks: 3` with 5 independent tasks → 3 running concurrently, then 2
- `max_parallel_tasks: 3` with a dependency chain A→B→C → serial execution (A, then B,
  then C), respecting edges
- `max_parallel_tasks: 2` with A (independent), B→C (chain) → A and B run in parallel,
  C waits for B
- A failing task in a parallel batch → in-flight siblings finish, no new tasks start,
  chunk reports failure
- Cycle in `depends_on` → clear error message before execution starts
- Split prompt produces `depends_on` edges for tasks with real ordering constraints
- New unit tests for DAG validation, parallel dispatch, hook serialization
- Integration test: parallel chunk execution completes correctly

# Notes

- Git worktree isolation (each parallel task gets a separate checkout) is the "real"
  solution for avoiding file conflicts. It's deferred because it's a large lift —
  managing worktrees, merging results, handling conflicts. For now, parallel tasks
  should be genuinely independent (different files). The split prompt guidance helps.
- The `ongoing.json` entries from PLAN-013 (claiming) compose naturally: each parallel
  task gets its own `active_runs` entry.
- `work.sequential_by_default` (existing config key) becomes redundant once
  `max_parallel_tasks` is available. We may deprecate it, but that's cleanup, not
  this plan.
