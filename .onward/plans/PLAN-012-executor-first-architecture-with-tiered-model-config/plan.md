---
id: "PLAN-012"
type: "plan"
project: ""
title: "Executor-first architecture with tiered model config"
status: "completed"
description: "Replace the double-subprocess executor hop with a first-class Executor protocol, built-in default that routes directly to Claude/Cursor CLIs, batch task support for chunk/plan work, and a simplified tiered model configuration with fallback chains."
priority: "high"
model: "composer-2"
created_at: "2026-03-20T21:48:51Z"
updated_at: "2026-03-21T00:17:40Z"
---

# Summary

Redesign Onward's execution layer around a first-class Python Executor protocol. The built-in default executor routes directly to Claude Code or Cursor agent CLIs (eliminating the double-subprocess hop through `onward-exec`). Batch task support lets `onward work CHUNK-*` enqueue all ready tasks and oversee them sequentially. A simplified tiered model config (`default`, `high`, `medium`, `low`, `split`, `review_1`, `review_2`) with automatic fallback chains replaces the current flat model keys.

# Problem

1. **Double subprocess hop.** `onward work` spawns `onward-exec`, which spawns `claude`. The indirection adds latency, makes streaming harder, and splits prompt construction across Python and a shell script.
2. **No pluggable executor contract.** The executor is just "whatever command is in config." There's no Python interface, no way to swap implementations, no batch support.
3. **Model config is flat and ad-hoc.** `models.default`, `task_default`, `split_default`, `review_default` don't express a tier hierarchy. Tasks can't declare effort level and get the right model automatically. Fallback behavior is inconsistent.
4. **No CLI routing.** The reference executor only routes to `claude`. There's no Cursor agent support. Adding a new CLI means editing `scripts/onward-exec`.
5. **No batch execution.** `onward work CHUNK-*` calls the executor once per task in a Python loop. The executor has no awareness of the batch; can't optimize, can't report progress across tasks.

# Goals

- A Python `Executor` ABC that any implementation can satisfy (built-in, external subprocess, future HTTP)
- A built-in executor that routes to Claude Code or Cursor agent based on model string, with streaming output
- Batch execution: `onward work CHUNK-*` sends all ready tasks to the executor, which runs them sequentially and yields results
- Tiered model config: `models.default`, `high`, `medium`, `low`, `split`, `review_1`, `review_2` with automatic fallback chains
- Tasks declare `effort: high|medium|low` to get the appropriate model tier
- External executors (subprocess + stdin JSON) still work via adapter, full backward compat
- `scripts/onward-exec` remains as a reference but is no longer the default path

# Non-goals

- Parallel task execution within a chunk (sequential only for now)
- HTTP/gRPC executor backends (protocol allows it, but only subprocess in this plan)
- Changing the executor payload JSON schema (external executors get the same shape)
- Removing `scripts/onward-exec` (it stays as a reference implementation)

# End state

- [ ] `models` config uses tiered keys: `default`, `high`, `medium`, `low`, `split`, `review_1`, `review_2`
- [ ] Fallback chains work: `low` -> `medium` -> `high` -> `default`; `review_1` -> `high` -> `default`; `review_2` -> `high` -> `default`; `split` -> `default`
- [ ] Tasks with `effort: low` automatically use `models.low` (with fallback)
- [ ] Old config keys (`task_default`, `split_default`, `review_default`) produce doctor warnings
- [ ] `Executor` ABC exists with `execute_task()` and `execute_batch()` methods
- [ ] `BuiltinExecutor` routes Claude models to `claude` CLI and Cursor models to `cursor` CLI
- [ ] `SubprocessExecutor` wraps the existing stdin JSON protocol for external executors
- [ ] `executor.command` absent or `"builtin"` uses built-in executor; any other value uses SubprocessExecutor
- [ ] `onward work CHUNK-*` uses batch execution (all ready tasks at once, results yielded per task)
- [ ] Streaming output: user sees AI output in real-time during built-in executor runs
- [ ] Prompt construction lives in Python (moved from `scripts/onward-exec`)
- [ ] All existing tests pass; new tests cover executor protocol, routing, model fallback, batch

# Context

The current system (PLAN-011 completed) has a working executor path: `execution.py` spawns `onward-exec` via subprocess, which reads JSON from stdin and spawns `claude`. This works but is indirect. The provider registry design in `docs/PROVIDER_REGISTRY.md` sketched multi-provider routing but was never implemented. This plan supersedes that design with a simpler, more practical approach: a Python protocol with a built-in default.

# Proposed approach

## Chunk 1: Tiered model config

Replace the current flat `models` section with a tiered system. All keys except `default` have fallback chains. Task-to-model resolution checks `effort` metadata.

**New config shape:**

```yaml
models:
  default: opus-latest
  high: opus-latest
  medium: sonnet-latest
  low: haiku-latest
  split: sonnet-latest
  review_1: null          # fallback: high -> default
  review_2: null          # fallback: high -> default
```

**Fallback chains (walk until non-null):**

- `high` -> `default`
- `medium` -> `high` -> `default`
- `low` -> `medium` -> `high` -> `default`
- `split` -> `default`
- `review_1` -> `high` -> `default`
- `review_2` -> `high` -> `default`

**Task-to-model resolution (in order):**

1. Explicit `model` in task frontmatter -> use as-is
2. `effort: high|medium|low` in task frontmatter -> map to tier
3. Neither -> `default`

**Migration:** Old keys produce `onward doctor` warnings; `default` replaces `default`, `split_default` maps to `split`, `review_default` maps to `review_1`.

**Files:** `src/onward/config.py`, `.onward.config.yaml`, `src/onward/scaffold.py`, tests

## Chunk 2: Executor protocol and external adapter

Define the Python interface and wrap the existing subprocess protocol for backward compat.

**New `src/onward/executor.py`:**

- `TaskContext` dataclass: task artifact, resolved model, run_id, plan/chunk context, notes
- `ExecutorResult` dataclass: task_id, run_id, success, output, error, ack, return_code
- `Executor` ABC: `execute_task(root, ctx) -> ExecutorResult` and `execute_batch(root, tasks) -> Iterator[ExecutorResult]`
- `SubprocessExecutor`: wraps `executor.command` + `executor.args`, builds JSON payload on stdin, parses output/ack
- `resolve_executor(config) -> Executor`: if `executor.command` is set and not `"builtin"`, return SubprocessExecutor; else return BuiltinExecutor

**Files:** `src/onward/executor.py` (new), `src/onward/config.py`, tests

## Chunk 3: Built-in executor

The default executor that directly spawns Claude Code or Cursor agent.

**New `src/onward/executor_builtin.py`:**

- `CLIBackend` base: `build_argv(model, prompt) -> list[str]`
- `ClaudeBackend`: `claude --model <model> -p <prompt>`
- `CursorBackend`: `cursor --agent --model <model> -p <prompt>`
- `route_model_to_backend(model) -> CLIBackend`: pattern-match model string
- `BuiltinExecutor(Executor)`: resolves backend, spawns via `Popen`, streams stdout/stderr to terminal and log, parses ack
- Prompt building functions moved from `scripts/onward-exec`: `build_task_prompt()`, `build_hook_prompt()`, `build_review_prompt()`

**Files:** `src/onward/executor_builtin.py` (new), tests

## Chunk 4: Batch execution and integration

Wire everything together: `onward work` uses the Executor protocol, chunk/plan work uses batch execution.

- Refactor `execution.py`: `_execute_task_run` delegates to `executor.execute_task()`, run record/status management stays in Onward
- `_work_chunk` collects all ready tasks, resolves models via tier+fallback, calls `executor.execute_batch()`, updates status as results yield
- Single-task `work_task()` is a one-element batch through the same path
- `_work_plan` iterates chunks using batch execution per chunk
- Hooks (pre/post shell, markdown) stay in Onward, not in the executor

**Files:** `src/onward/execution.py`, `src/onward/cli_commands.py`, tests

## Chunk 5: Docs, config validation, and cleanup

- Update `PROVIDER_REGISTRY.md` to point at new architecture (or archive)
- Update `CAPABILITIES.md` for built-in executor, batch semantics
- Update `LIFECYCLE.md` for batch chunk/plan execution
- Extend config validation (`onward doctor`) for new model keys, executor resolution
- Architecture seam tests for new modules
- Comprehensive tests: executor protocol, CLI routing, model fallback chains, batch execution, external adapter

**Files:** docs, `src/onward/config.py`, `tests/`

# Acceptance criteria

- [ ] `models` config accepts `default`, `high`, `medium`, `low`, `split`, `review_1`, `review_2`
- [ ] `model_setting()` resolves fallback chains correctly (unit tests)
- [ ] Old config keys produce `onward doctor` warnings
- [ ] `Executor` ABC is importable from `onward.executor`
- [ ] `BuiltinExecutor` routes `opus-latest` to `claude` CLI
- [ ] `BuiltinExecutor` routes `cursor-*` models to `cursor` CLI
- [ ] `SubprocessExecutor` produces identical behavior to current `_execute_task_run` with external executor
- [ ] `onward work CHUNK-*` uses batch execution (observable in run logs)
- [ ] Streaming output visible during `BuiltinExecutor` runs
- [ ] `effort: low` on a task resolves to `models.low` (with fallback)
- [ ] All existing tests pass
- [ ] `onward doctor` validates new config shape

# Notes

Chunk 1 (model config) has no dependency on the executor work and can land independently. Chunk 2 (protocol) is the foundation for chunks 3-4. Chunk 3 (built-in executor) can be developed in parallel with chunk 4 (integration) but chunk 4 depends on chunk 2. Chunk 5 is last since it's documentation and cleanup.
