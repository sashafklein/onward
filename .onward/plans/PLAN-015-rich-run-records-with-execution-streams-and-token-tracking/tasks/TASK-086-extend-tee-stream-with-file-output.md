---
id: "TASK-086"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-025"
project: ""
title: "Extend _tee_stream with optional file_out parameter"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: ["TASK-084"]
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:40:00Z"
---

# Context

`_tee_stream` in `executor_builtin.py` reads lines from a subprocess pipe and
writes them to the terminal. It needs a second write target: the `output-*.log`
file opened from `PreparedTaskRun.output_log`.

# Scope

- Add `file_out: TextIO | None = None` and `file_lock: threading.Lock | None = None` parameters to `_tee_stream`
- Inside the loop, after writing to `tee_to`, if `file_out` is not None:
  - Acquire `file_lock` (if provided), write the line, flush, release
- Update callers of `_tee_stream` to pass the new parameters

# Out of scope

- Opening/closing the file handle (TASK-087)
- SubprocessExecutor changes

# Files to inspect

- `src/onward/executor_builtin.py` — `_tee_stream` function signature and body

# Implementation notes

- The lock prevents stdout and stderr lines from interleaving mid-line in the output file
- `tee_to.flush()` is already called; add `file_out.flush()` inside the lock
- Keep `file_out=None` as default so callers without streaming don't break

# Acceptance criteria

- [ ] `_tee_stream` signature updated with `file_out` and `file_lock` parameters
- [ ] Each line written to `file_out` is flushed immediately
- [ ] Existing `_tee_stream` callers that don't pass `file_out` continue to work unchanged
- [ ] Unit test: mock `file_out` and verify every line is written to it

# Handoff notes

TASK-087 opens the file and wires it into both tee threads.
