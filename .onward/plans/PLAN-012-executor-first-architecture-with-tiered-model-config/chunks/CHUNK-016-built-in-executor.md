---
id: "CHUNK-016"
type: "chunk"
plan: "PLAN-012"
project: ""
title: "Built-in executor"
status: "completed"
description: "Implement BuiltinExecutor with CLI routing to Claude/Cursor, streaming Popen output, and prompt construction moved from scripts/onward-exec."
priority: "high"
model: "composer-2"
depends_on:
- "CHUNK-015"
created_at: "2026-03-20T21:50:09Z"
updated_at: "2026-03-20T22:34:48Z"
---

# Summary

Build the default executor that runs when no external `executor.command` is configured. It routes model strings to the appropriate CLI backend (Claude Code or Cursor agent), constructs prompts in Python (eliminating the `scripts/onward-exec` indirection), and streams subprocess output to both the terminal and run log files in real-time.

# Scope

- `CLIBackend` base with `build_argv(model, prompt) -> list[str]`
- `ClaudeBackend`: invokes `claude --model <model> -p <prompt>`
- `CursorBackend`: invokes `cursor --agent --model <model> ...`
- `route_model_to_backend(model) -> CLIBackend`: pattern-match model string to backend
- `BuiltinExecutor(Executor)`: resolves backend, spawns via `Popen`, streams output, parses ack
- Prompt building functions: `build_task_prompt()`, `build_hook_prompt()`, `build_review_prompt()` moved from `scripts/onward-exec` into Python
- Real-time streaming: stdout/stderr written to terminal and log file simultaneously

# Out of scope

- Batch execution wiring (chunk 4)
- HTTP/gRPC backends (future)
- Removing `scripts/onward-exec` (stays as reference)

# Dependencies

- CHUNK-015 (executor protocol) -- BuiltinExecutor implements the Executor ABC

# Expected files/systems involved

- `src/onward/executor_builtin.py` -- new file: BuiltinExecutor, CLI backends, prompt building
- `scripts/onward-exec` -- reference for prompt building logic to port
- `tests/` -- routing tests, prompt building tests, mock subprocess tests

# Completion criteria

- [ ] `BuiltinExecutor` satisfies the `Executor` ABC
- [ ] `route_model_to_backend("opus-latest")` returns ClaudeBackend
- [ ] `route_model_to_backend("cursor-fast")` returns CursorBackend
- [ ] Default (unknown model) falls back to ClaudeBackend
- [ ] Prompt building produces equivalent output to `scripts/onward-exec`
- [ ] `Popen` streaming works: output visible in real-time and captured to log
- [ ] `onward_task_result` ack parsed from streaming output
