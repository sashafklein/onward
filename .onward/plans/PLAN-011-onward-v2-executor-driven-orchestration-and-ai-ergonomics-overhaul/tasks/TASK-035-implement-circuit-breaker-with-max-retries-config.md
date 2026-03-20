---
id: "TASK-035"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-009"
project: ""
title: "Implement circuit breaker with max_retries config"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: ["TASK-034"]
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:02Z"
updated_at: "2026-03-20T16:01:02Z"
---

# Context

After TASK-034 adds the `failed` status and `run_count` tracking, this task adds a circuit breaker: a configurable `work.max_retries` setting that prevents `onward work` from running a task that has already failed too many times. This protects against infinite retry loops when an AI agent keeps re-running the same broken task.

# Scope

- Add `"max_retries"` to `CONFIG_SECTION_KEYS["work"]` in `config.py`
- Add `work_max_retries(config) -> int` helper in `config.py` (reads `work.max_retries`, default 3)
- In `work_task()` in `execution.py`, before executing: check `run_count` against `work_max_retries(config)` and raise `ValueError` with actionable message if exceeded
- In `cmd_work` chunk loop in `cli_commands.py`: when a task is circuit-broken, skip it (print warning) and continue with other ready tasks
- Update `.onward.config.yaml` scaffold default in `scaffold.py` to include `max_retries: 3` under `work:`
- Update `docs/LIFECYCLE.md` with circuit breaker behavior
- Add tests for circuit breaker threshold, skip behavior in chunk mode, config override

# Out of scope

- Exponential backoff or delay between retries
- Per-task `max_retries` override in task frontmatter
- Resetting `run_count` on retry (that's TASK-034's `onward retry` responsibility)
- Any UI beyond CLI output for circuit breaker status

# Files to inspect

- `src/onward/config.py` — `CONFIG_SECTION_KEYS["work"]` (line ~25), add `work_max_retries` helper near `work_require_success_ack`
- `src/onward/execution.py` — `work_task()` (line ~348) for pre-execution check
- `src/onward/cli_commands.py` — `cmd_work()` chunk loop (line ~582) to handle circuit-broken tasks
- `src/onward/scaffold.py` — `DEFAULT_FILES[".onward.config.yaml"]` for scaffold update
- `docs/LIFECYCLE.md` — circuit breaker documentation

# Implementation notes

- `work_max_retries` should return an int. If the config value is absent or empty, default to 3. If set to 0, treat as "unlimited" (no circuit breaker).
- The circuit breaker check in `work_task()` should happen BEFORE setting the task to `in_progress`. This prevents the status from cycling on each attempt. Pattern:
  ```python
  run_count = int(task.metadata.get("run_count", 0))
  max_retries = work_max_retries(config)
  if max_retries > 0 and run_count >= max_retries:
      raise ValueError(f"TASK-X has failed {run_count} times (max_retries={max_retries}); ...")
  ```
- In the chunk loop, catch the circuit breaker `ValueError` specifically. Print a warning line and continue to the next ready task. This is different from other errors which stop the chunk.
- `onward retry TASK-X` (from TASK-034) resets `run_count` to 0, effectively resetting the circuit breaker.
- The `validate_config_contract_issues` function doesn't need changes — the key is already in the allowed set after adding it to `CONFIG_SECTION_KEYS`.

# Acceptance criteria

- `onward work TASK-X` refuses to run when `run_count >= max_retries` with clear error
- Error message includes retry count, max, and `onward retry` hint
- `onward work CHUNK-X` skips circuit-broken tasks and continues with others
- Default `max_retries` is 3
- Setting `max_retries: 0` disables the circuit breaker (unlimited retries)
- `.onward.config.yaml` scaffold includes `max_retries: 3`
- `docs/LIFECYCLE.md` documents circuit breaker behavior
- Tests cover: threshold enforcement, skip in chunk mode, config override, disabled breaker

# Handoff notes

- This completes the retry/circuit-breaker feature pair with TASK-034.
- Future enhancement: per-task `max_retries` override in task frontmatter.
- Future enhancement: exponential backoff delay between retries.
- The `cmd_work` chunk loop currently stops on failure — the circuit breaker skip is new behavior where it continues past failed-and-maxed tasks.
