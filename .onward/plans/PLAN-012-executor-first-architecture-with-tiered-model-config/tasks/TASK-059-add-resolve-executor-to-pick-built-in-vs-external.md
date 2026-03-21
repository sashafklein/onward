---
id: "TASK-059"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-015"
project: ""
title: "Add resolve_executor to pick built-in vs external"
status: "completed"
description: "Implement resolve_executor(config) that returns SubprocessExecutor for external commands or BuiltinExecutor for the default path."
human: false
model: "composer-2"
effort: "small"
depends_on:
- "TASK-058"
files:
- "src/onward/config.py"
- "src/onward/executor.py"
acceptance:
- "resolve_executor returns SubprocessExecutor when executor.command is set"
- "resolve_executor returns BuiltinExecutor when command is absent or 'builtin'"
- "BuiltinExecutor can be a stub/placeholder until CHUNK-016"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:27:54Z"
run_count: 1
last_run_status: "completed"
---

# Context

The glue that decides which executor implementation to use based on config. This needs to exist before CHUNK-016 builds the real BuiltinExecutor, so it can return a placeholder initially.

# Scope

- `resolve_executor(config: dict) -> Executor` in `src/onward/config.py`:
  - If `executor.command` is set and not empty and not `"builtin"`, return `SubprocessExecutor(command, args)`
  - Otherwise, return `BuiltinExecutor(config)` (placeholder that raises NotImplementedError until CHUNK-016)
- Update `CONFIG_TOP_LEVEL_KEYS` and `CONFIG_SECTION_KEYS` if needed for any new executor config keys

# Out of scope

- Real BuiltinExecutor implementation (CHUNK-016)
- Wiring resolve_executor into execution.py (CHUNK-017)

# Files to inspect

- `src/onward/config.py` -- `_workspace_executor_argv()`, config loading
- `.onward.config.yaml` -- current executor config shape

# Implementation notes

- The BuiltinExecutor placeholder can live in `executor.py` temporarily as a minimal class that raises NotImplementedError
- `executor.command: "builtin"` is an explicit way to say "use built-in" even when the key is present

# Acceptance criteria

- [ ] `resolve_executor({"executor": {"command": "onward-exec"}})` returns SubprocessExecutor
- [ ] `resolve_executor({})` returns BuiltinExecutor
- [ ] `resolve_executor({"executor": {"command": "builtin"}})` returns BuiltinExecutor
- [ ] `resolve_executor({"executor": {"command": ""}})` returns BuiltinExecutor
