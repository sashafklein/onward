# Capability truth table

Short reference for **what is model-backed**, what is **local/heuristic**, and what exists only for **tests**. Keeps docs and mental models aligned with `src/onward/` (PLAN-010).

## Executor-backed (subprocess + stdin JSON)

These invoke the command from `ralph.command` (and `ralph.args`) when `ralph.enabled` is true, subject to each command’s checks:

| Feature | Notes |
| ------- | ----- |
| `onward work TASK-*` | Full task payload + hooks; see [WORK_HANDOFF.md](WORK_HANDOFF.md). |
| `onward work CHUNK-*` | Same per ready task; `post_chunk_markdown` hook after all tasks succeed. |
| `onward review-plan` | One or two reviewer runs (`review.double_review`). |
| Markdown hooks | `pre_task_markdown`, `post_task_markdown`, `post_chunk_markdown` (shell hooks are **not** the executor). |

If `ralph.enabled` is false, executor-backed steps are skipped or fail with a clear message (shell hooks may still run).

## Local / no model call

| Feature | Notes |
| ------- | ----- |
| `onward split PLAN-*` / `CHUNK-*` | **Heuristic only today:** derives candidate chunks/tasks from markdown sections (e.g. Goals, Scope, Completion criteria) and builds JSON locally. Does **not** call the executor or an external model in the default code path. |
| `onward new`, `list`, `show`, `tree`, `report`, `next`, `progress`, `recent` | Filesystem + derived indexes. |
| `onward start` / `complete` / `cancel` | Status transitions only; see [LIFECYCLE.md](LIFECYCLE.md). |
| `onward note`, `onward archive` | File updates. |
| `onward doctor` | Config/workspace validation. |
| `onward sync` | Git operations; no LLM. |

The `split` code path still accepts **`--model`** and writes **`model`** into new chunk/task metadata — that selects defaults for **future** `onward work`, not an LLM call during split.

## Test / development overrides

| Mechanism | Purpose |
| --------- | ------- |
| `TRAIN_SPLIT_RESPONSE` | If set, `onward split` uses this string as the JSON response instead of heuristics (tests and local experiments). |

## Lifecycle vs capabilities

Artifact status rules are **orthogonal** to model usage: see [LIFECYCLE.md](LIFECYCLE.md) for `start` / `work` / `complete` / `cancel`.
