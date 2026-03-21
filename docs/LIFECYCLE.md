# Artifact lifecycle policy (PLAN-010)

This document is the **authoritative** description of how Onward moves plans, chunks, and tasks through `open` → `in_progress` → `completed` / `canceled` / `failed`. CLI errors and tests are written to match this text (see `onward complete` / `cancel` / `retry` / `work`).

## Decision: work-owned execution, manual overlays

Onward uses **one** coherent model:

1. **`onward work` owns status changes that surround executor-backed runs** — it sets work to `in_progress`, runs hooks + executor, then sets a **task** to `completed` on success or **`failed`** on failure (see **`onward retry`** to reset a failed task to `open`). **`onward work CHUNK-*`** similarly drives the chunk to `in_progress` while tasks run, runs the chunk post hook, then sets the chunk to **`completed`** when all ready work succeeds. **`onward work PLAN-*`** walks every chunk in the plan (skipping `completed` / `canceled` chunks), in chunk-ID order with `depends_on` respected, running each chunk the same way as **`onward work CHUNK-*`**, then sets the plan to **`completed`** when all chunks finish successfully.

2. **`onward complete`, `onward cancel`, and `onward retry` are explicit manual transitions** — they do **not** invoke the executor. Use them for closing work done **outside** `onward work`, abandoning items, or resetting **`failed`** tasks. **`in_progress`** for execution is set only by **`onward work`** (or by editing artifacts out-of-band).

This is **not** a strict manual state machine: after a **successful** `onward work TASK-*`, the task is already **`completed`**; running `onward complete` on it would fail (invalid transition from `completed`).

## Status vocabulary

| Status         | Meaning |
| -------------- | ------- |
| `open`         | Not started, or reset with **`onward retry`** after a failure. |
| `in_progress`  | Actively claimed or currently running under `work`. |
| `failed`       | Last **`onward work`** run did not succeed; not offered by **`onward next`**. Use **`onward retry`** then **`onward work`** again. |
| `completed`    | Terminal success. |
| `canceled`     | Terminal abandon. |

## Manual commands (`complete` / `cancel` / `retry`)

Allowed transitions (enforced today when invoking these commands):

| Command    | From `open`     | From `in_progress` | From `failed` |
| ---------- | --------------- | ------------------ | ------------- |
| `complete` | → `completed`   | → `completed`      | *(invalid)*   |
| `cancel`   | → `canceled`    | → `canceled`       | *(invalid)*   |
| `retry`    | *(invalid)*     | *(invalid)*        | → `open`      |

Applies to **any** artifact type (plan, chunk, task) that uses the shared status field. Invalid transitions raise an error with a clear message.

## `onward work TASK-*`

- **From:** `open` or `in_progress` (not `completed` / `canceled` / `failed`). A **`failed`** task must be reset with **`onward retry`** before it can run again.
- **Behavior:** increment **`run_count`**, set task `in_progress` → run execution pipeline → on success set **`completed`** and **`last_run_status: completed`**; on failure set **`failed`** and **`last_run_status: failed`**, and record the failed run.

### Circuit breaker (`work.max_retries`)

After each run (success or failure), **`run_count`** reflects how many times the task has started. **`work.max_retries`** (default **3**) is a ceiling on **`run_count`** before **`onward work`** refuses to start another run: if **`run_count` ≥ `max_retries`**, the CLI raises an error (single task) or prints a **Warning** and tries the next ready task (**`onward work CHUNK-*`**). Set **`work.max_retries: 0`** to disable the breaker (unlimited attempts). **`onward retry`** resets **`run_count`** to 0 and clears the breaker for that task.

**`complete` after success:** unnecessary; the task is already `completed`.

## `onward work CHUNK-*`

- While the chunk has runnable work, the chunk is kept in **`in_progress`** (if it was `open` or already `in_progress`).
- **Batch waves:** Onward repeatedly selects **ready** tasks (dependency order, `work.max_retries`, and `work.sequential_by_default`). For each **wave**, it prepares every **eligible** task (status, hooks, run records), then invokes **`Executor.execute_batch`** **once** with the full list of `TaskContext` values for that wave. The iterator runs tasks **one after another** in wave order: for each task, `pre_task_shell` runs, then the next batch step runs the executor, then post-task shell and `post_task_markdown` on success. If any task in the wave fails, chunk processing stops (same as a single-task failure). When `work.sequential_by_default` is **false**, a wave contains at most **one** task unless you run `onward work CHUNK-*` again for the next task.
- This is the same **semantic** pipeline as `onward work TASK-*`, but chunk work gives the executor a **batch iterator** for the wave so the built-in executor (or a custom `Executor`) can align with multi-step runs; hooks and status updates remain in Onward.
- After all tasks that can run have **completed** successfully, the **post_chunk** markdown hook runs; on success the chunk is set to **`completed`**.

If a task fails, chunk processing stops with a non-zero exit; the chunk usually remains **`in_progress`** until you resolve tasks and run `work` again or adjust status manually. The CLI prints a short hint pointing here.

When **every** task in a chunk reaches a **terminal** state (`completed` or `canceled`) — including via `onward complete` rather than `onward work` — Onward will run the **post_chunk** hook (when configured) and set the chunk to **`completed`** on success. **`failed`** tasks are not terminal for this rule (the chunk stays active until you **`retry`**, **`complete`**, or **`cancel`** those tasks). This runs when you next run **`onward next`**, **`onward report`**, or **`onward complete`** on a task, and after a successful **`onward work TASK-*`** that finishes the last non-terminal task in the chunk.

## `onward work PLAN-*`

- **From:** plan in `open` or `in_progress` (not `completed` / `canceled`).
- **Behavior:** set plan **`in_progress`**, then for each child chunk (sorted by chunk ID; skip chunks already **`completed`** or **`canceled`**; honor chunk **`depends_on`** so a chunk runs only when its dependencies are **`completed`**) run the same pipeline as **`onward work CHUNK-*`** — including **batch waves** per chunk (`execute_batch` per wave of ready tasks). Stop on the first chunk or task failure; the plan stays **`in_progress`** so you can fix work and re-run. When every chunk has been processed successfully, set the plan to **`completed`**.

If the plan has **no** chunks, the command succeeds with a short message and does not change plan status beyond what is already implied. If the plan is **already** `completed`, the CLI prints that and exits **0**.

## Choosing a command (quick reference)

| Goal | Command |
| ---- | ------- |
| Run the executor for a task with full context | `onward work TASK-*` |
| Drain a chunk’s ready tasks (and post hook) | `onward work CHUNK-*` |
| Run every remaining chunk in a plan, in order | `onward work PLAN-*` |
| Reset a **failed** task so `work` can run again | `onward retry TASK-*` |
| Close work **without** using `work` | `onward complete` |
| Abandon | `onward cancel` |

## Dependencies (`depends_on`)

Use **`depends_on: [TASK-###, …]`** (and chunk/plan equivalents) for ordering: a task is not runnable until every listed ID is **`completed`**. The legacy **`blocked_by`** field is **deprecated** but still read with the **same** completion-based semantics; `onward doctor` warns if **`blocked_by`** is present. Prefer **`depends_on`** for new and edited artifacts.

## Relationship to agent docs

Repository **AGENTS.md** and **INSTALLATION.md** agent blocks should match this policy. If they disagree, **this file and the CLI win**. **[AI_OPERATOR.md](AI_OPERATOR.md)** is a shorter operator-facing summary (loop, pitfalls, recovery); it should not contradict this file.

## Related docs

- **[AI_OPERATOR.md](AI_OPERATOR.md)** — quickstart and anti-patterns for agents/operators.
- **[RECOVERY.md](RECOVERY.md)** — failed runs, logs, retry/cancel, circuit breaker, hooks.
- **[CAPABILITIES.md](CAPABILITIES.md)** — model-backed vs heuristic commands (orthogonal to lifecycle).
