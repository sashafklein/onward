---
id: "TASK-062"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-016"
project: ""
title: "Implement BuiltinExecutor with streaming Popen output"
status: "completed"
description: "Implement the BuiltinExecutor class that routes to CLI backends, streams output via Popen, and parses ack from output."
human: false
model: "composer-2"
effort: "large"
depends_on:
- "TASK-060"
- "TASK-061"
files:
- "src/onward/executor_builtin.py"
- "src/onward/executor.py"
acceptance:
- "BuiltinExecutor satisfies the Executor ABC"
- "Spawns correct CLI based on model routing"
- "Output streams to terminal in real-time via Popen"
- "Output simultaneously captured for run log"
- "onward_task_result ack parsed from output stream"
- "FileNotFoundError (CLI not installed) returns failed ExecutorResult"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:34:48Z"
run_count: 1
last_run_status: "completed"
---

# Context

The core built-in executor that replaces the double-subprocess hop. This is the most complex task in the chunk -- it handles subprocess lifecycle, streaming I/O, and ack parsing.

# Scope

- `BuiltinExecutor(Executor)` in `src/onward/executor_builtin.py`:
  - Constructor takes `config: dict` for any future config needs
  - `execute_task(root, ctx)`:
    1. Build prompt via `build_task_prompt(ctx)`
    2. Route model to backend via `route_model_to_backend(ctx.model)`
    3. Check backend executable exists (`find_executable`)
    4. Build argv via `backend.build_argv(ctx.model, prompt)`
    5. Spawn via `subprocess.Popen(argv, stdout=PIPE, stderr=PIPE, ...)`
    6. Stream stdout/stderr to sys.stdout/sys.stderr in real-time (use threads or select)
    7. Simultaneously accumulate output for run log
    8. Parse `onward_task_result` ack from accumulated output
    9. Return `ExecutorResult`
  - Replace the placeholder from TASK-059 with the real implementation
- Handle edge cases: CLI not found, non-zero exit, timeout (optional)
- Set `ONWARD_RUN_ID` in subprocess env

# Out of scope

- Batch execution override (default ABC loop is fine for now)
- Hook execution (stays in execution.py)
- Review execution via BuiltinExecutor (future)

# Files to inspect

- `scripts/onward-exec` -- `run_claude()` for current subprocess pattern
- `src/onward/executor_ack.py` -- `find_task_success_ack()` for ack parsing

# Implementation notes

- Use `threading.Thread` to read stdout and stderr simultaneously without blocking
- Each thread reads line-by-line, writes to terminal, and appends to a buffer
- After process completes, join threads and scan buffers for ack JSON
- Consider a `_StreamCapture` helper class to encapsulate the read-and-tee logic
- `Popen.wait()` after threads are joined to get return code

# Acceptance criteria

- [ ] `BuiltinExecutor` is a valid `Executor` subclass
- [ ] Claude model task spawns `claude --model X -p ...`
- [ ] Cursor model task spawns `cursor --agent --model X -p ...`
- [ ] Output visible on terminal during execution (not just at end)
- [ ] Output captured in ExecutorResult.output for logging
- [ ] Ack parsed correctly when present in output
- [ ] Missing CLI returns `ExecutorResult(success=False, error="... not found")`
- [ ] `ONWARD_RUN_ID` set in subprocess environment
