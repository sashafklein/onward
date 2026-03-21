---
id: "CHUNK-025"
type: "chunk"
plan: "PLAN-015"
project: ""
title: "Live output streaming to output-*.log"
status: "completed"
description: ""
priority: "medium"
model: "sonnet-latest"
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:56:20Z"
---

# Summary

Wires the `output-*.log` file (introduced by CHUNK-024) into the `BuiltinExecutor`'s
streaming tee threads so that every line the executor emits is written to disk in
real time. This makes it possible to `tail -f` the log from another terminal while a
task is running.

# Scope

- Extend `_tee_stream` in `executor_builtin.py` to accept an optional `file_out: TextIO` and flush-write each line there
- Open `output_log` from `PreparedTaskRun` before spawning the subprocess; pass the handle to both stdout and stderr tee threads
- Close the handle after both threads join
- Use a threading lock for interleaved stdout/stderr writes so lines don't corrupt each other

# Out of scope

- SubprocessExecutor streaming (non-priority path; noted as follow-up in plan)
- Rotating or size-capping the output log (FUTURE_ROADMAP.md)

# Dependencies

- CHUNK-024 (provides `PreparedTaskRun.output_log` path)

# Expected files/systems involved

- `src/onward/executor_builtin.py` — `_tee_stream`, `BuiltinExecutor.execute_task`
- `src/onward/execution.py` — passes `output_log` path to executor invocation

# Completion criteria

- [ ] `output-*.log` is created and non-empty before the task subprocess exits
- [ ] A second terminal running `tail -f .onward/runs/TASK-XXX/output-<ts>.log` shows live output
- [ ] stdout and stderr are both written to the file without interleaving corruption
- [ ] File handle is always closed (even on subprocess failure)

# Notes

The file should be opened in `"w"` mode (text, UTF-8). A `threading.Lock` shared between the two tee threads ensures atomic line writes.
