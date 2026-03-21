# Recovery from failed execution

When **`onward work`** fails, use this guide to see what broke, where to look, and what to do next. Lifecycle rules: **[LIFECYCLE.md](LIFECYCLE.md)**.

## Quick reference

| Symptom | What to do |
| -------- | ---------- |
| Task **`failed`**, fix is obvious | **`onward retry TASK-*`** then **`onward work TASK-*`** |
| Same task keeps failing | Read **run log** (below); adjust task body or config; retry |
| **`run_count` at `work.max_retries`** (circuit open) | **`onward retry TASK-*`** (resets counter) or raise **`work.max_retries`** in config |
| Wrong work item; abandon | **`onward cancel TASK-*`** and add a replacement task if needed |
| Human judgment required | Set **`human: true`** on the task (or a follow-up) and hand off |

## Reading run logs

1. Find the run id from **`onward show TASK-*`** (Run history) or stderr from **`onward work`**.
2. Open **`.onward/runs/RUN-*-<TASK>.log`** (path also on the run record).

Log sections (in order when present):

| Section | Meaning |
| -------- | -------- |
| `$ <command>` | Executor command line |
| `[pre_task_shell]` / `[post_task_shell]` | Shell hooks; non-zero exit fails the run |
| `[task stdout]` / `[task stderr]` | Executor output |
| `[post_task_markdown]` / `[post_chunk_markdown]` | Markdown hooks piped to the executor |
| `[error]` | Why Onward marked the run failed |

## Run record JSON

Files **`.onward/runs/RUN-*-<TASK>.json`** include:

- **`id`**, **`target`**, **`status`** (`running` / `completed` / `failed`), **`model`**, **`started_at`**, **`finished_at`**
- **`log_path`**, **`error`** (string; empty on success)
- **`success_ack`** — raw executor JSON line when a success acknowledgment was captured
- **`task_result`** — normalized structured result (summary, files changed, follow-ups, acceptance lists) when an ack was present

Use **`onward show TASK-*`** for a readable summary without opening files.

## Common failure modes

| Mode | Typical cause |
| ----- | ---------------- |
| Executor not found | **`executor.command`** wrong or not on `PATH` |
| Preflight / hook failure | Hook command missing, bad path, or non-zero exit |
| Timeout / hung process | Executor or model CLI stuck; kill process; fix script |
| Model / tool errors | Non-zero exit or stderr from the AI CLI |
| Missing success ack | **`work.require_success_ack: true`** but executor did not print **`onward_task_result`** JSON |
| Circuit breaker | **`run_count`** ≥ **`work.max_retries`** (see LIFECYCLE) |

## Recovery actions

### Retry

```bash
onward retry TASK-###
onward work TASK-###
```

Only **`failed`** tasks accept **`retry`** (resets to **`open`** and clears **`run_count`** per LIFECYCLE).

### Skip (abandon)

```bash
onward cancel TASK-###
```

If work still matters, create a follow-up with **`onward new task CHUNK-* "…"`**.

### Intervene

1. Edit the task markdown (scope, acceptance, notes).
2. **`onward retry TASK-*`** if it is **`failed`**, or leave **`open`**.
3. **`onward work TASK-*`** again.

### Chunk / plan stuck

- Fix or **`cancel`** failed tasks, **`retry`** where appropriate, then **`onward work CHUNK-*`** or **`PLAN-*`** again.
- **`onward report`** shows what is still runnable.

## Circuit breaker (`work.max_retries`)

When **`run_count`** reaches the configured maximum, **`onward work`** refuses another run for that task until you **`onward retry`** (clears the counter) or change config. Set **`work.max_retries: 0`** for unlimited attempts.

## Hook failures

Inspect the **`[pre_task_shell]`** / **`[post_task_shell]`** / **`[pre_chunk_shell]`** sections first. Fix commands in **`.onward.config.yaml`**. Markdown hooks appear under **`[post_task_markdown]`** / **`[post_chunk_markdown]`**; ensure **`executor.enabled`** and **`executor.command`** are valid when hooks invoke the executor.

## Escalation (human)

Use **`human: true`** when a person must decide (access, product judgment, production risk). **`onward next`** skips human tasks by default; complete them manually or adjust metadata after review.
