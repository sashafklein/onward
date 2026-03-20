# Artifact lifecycle policy (PLAN-010)

This document is the **authoritative** description of how Onward moves plans, chunks, and tasks through `open` → `in_progress` → `completed` / `canceled`. CLI errors and tests are written to match this text (see `onward start` / `complete` / `cancel` / `work`).

## Decision: work-owned execution, manual overlays

Onward uses **one** coherent model:

1. **`onward work` owns status changes that surround executor-backed runs** — it sets work to `in_progress`, runs hooks + executor, then sets a **task** to `completed` on success or back to **`open`** on failure (so it can be retried). **`onward work CHUNK-*`** similarly drives the chunk to `in_progress` while tasks run, runs the chunk post hook, then sets the chunk to **`completed`** when all ready work succeeds.

2. **`onward start`, `onward complete`, and `onward cancel` are explicit manual transitions** — they do **not** invoke the executor. Use them for visibility (“claim” work), closing work done **outside** `onward work`, or abandoning items.

This is **not** a strict “always `start` → manual work → always `complete`” loop: after a **successful** `onward work TASK-*`, the task is already **`completed`**; running `onward complete` on it would fail (invalid transition from `completed`).

## Status vocabulary

| Status         | Meaning |
| -------------- | ------- |
| `open`         | Not started, or task failed last run and may be retried with `work`. |
| `in_progress`  | Actively claimed or currently running under `work`. |
| `completed`    | Terminal success. |
| `canceled`     | Terminal abandon. |

## Manual commands (`start` / `complete` / `cancel`)

Allowed transitions (enforced today when invoking these commands):

| Command    | From `open`     | From `in_progress` |
| ---------- | --------------- | -------------------- |
| `start`    | → `in_progress` | *(invalid)*          |
| `complete` | → `completed`   | → `completed`        |
| `cancel`   | → `canceled`    | → `canceled`         |

Applies to **any** artifact type (plan, chunk, task) that uses the shared status field. Invalid transitions raise an error with a clear message.

## `onward work TASK-*`

- **From:** `open` or `in_progress` (not `completed` / `canceled`).
- **Behavior:** set task `in_progress` → run execution pipeline → on success set **`completed`**; on failure set **`open`** and record the failed run.

**`start` is optional:** you may run `work` directly from `open` without a prior `start`.

**`complete` after success:** unnecessary; the task is already `completed`.

## `onward work CHUNK-*`

- While the chunk has runnable work, the chunk is kept in **`in_progress`** (if it was `open` or already `in_progress`).
- Ready tasks are chosen in dependency order; each task is executed via the same path as `onward work TASK-*`.
- After all tasks that can run have **completed** successfully, the **post_chunk** markdown hook runs; on success the chunk is set to **`completed`**.

If a task fails, chunk processing stops with a non-zero exit; the chunk usually remains **`in_progress`** until you resolve tasks and run `work` again or adjust status manually. The CLI prints a short hint pointing here.

## Choosing a command (quick reference)

| Goal | Command |
| ---- | ------- |
| Run the executor for a task with full context | `onward work TASK-*` |
| Drain a chunk’s ready tasks (and post hook) | `onward work CHUNK-*` |
| Mark in flight for reporting without running yet | `onward start` *(optional)* |
| Close work **without** using `work` | `onward complete` |
| Abandon | `onward cancel` |

## Relationship to agent docs

Repository **AGENTS.md** and **INSTALLATION.md** agent blocks should match this policy. If they disagree, **this file and the CLI win** until docs are updated (see PLAN-010 **TASK-010**).

## Follow-up (other tasks)

- **TASK-010** — Propagate the same rules through README, INSTALLATION, CONTRIBUTION, and examples (if any drift remains).
