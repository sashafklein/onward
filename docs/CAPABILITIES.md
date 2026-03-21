# Capability truth table

Short reference for **what is model-backed**, what is **local/heuristic**, and what exists only for **tests**. Keeps docs and mental models aligned with `src/onward/`.

## Executor-backed

When `executor.enabled` is true, task work and split (non-heuristic) invoke an **executor implementation**:

- **Built-in (default):** if `executor.command` is **absent**, empty, or the literal **`builtin`** (case-insensitive), Onward uses **`BuiltinExecutor`**. It builds prompts in Python, resolves **Claude Code** vs **Cursor agent** from the model string, and runs the CLI directly with **streamed** stdout/stderr to your terminal (and run logs). See [`executor_builtin.py`](../src/onward/executor_builtin.py) (`route_model_to_backend`).
- **External subprocess:** if `executor.command` is set to any **other** string, Onward uses **`SubprocessExecutor`**: `[command, *args]` receives the same **stdin JSON** shape as before (`schema_version`, task payload, etc.). Output is captured for logs (not streamed interactively like the built-in path).

**Parallel task execution:** `work.max_parallel_tasks` (integer, default 1) controls how many ready tasks within a chunk can run concurrently. When set to 1 (default), behavior is identical to previous serial execution. When greater than 1, independent tasks (those whose `depends_on` dependencies are all completed) are dispatched simultaneously up to the limit. Before the task loop starts, Onward validates the `depends_on` graph for cycles and dangling references; any error aborts the chunk with a clear message. Post-task shell and markdown hooks are serialized across parallel tasks to prevent concurrent git-commit conflicts.

**Strict task completion:** when `work.require_success_ack` is true, a successful **`onward work TASK-*`** requires a machine-readable JSON line on executor stdout/stderr (not exit 0 alone); see [WORK_HANDOFF.md](WORK_HANDOFF.md) and [schemas/onward-task-success-ack-v1.schema.json](schemas/onward-task-success-ack-v1.schema.json). The executor receives **`ONWARD_RUN_ID`** in its environment (matches stdin `run_id`).

**Preflight:** before executor-backed `onward work`, `onward review-plan`, and `post_chunk_markdown`, Onward checks the **configured command** when a subprocess executor is used: a **bare name** must resolve via `PATH` (`shutil.which`); an **explicit path** must exist and be executable. The **built-in** executor skips argv0 preflight (it checks `claude` / `cursor` at run time). Commands `true` and `false` skip the check so tests work. See [`preflight.py`](../src/onward/preflight.py).

| Feature                           | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `onward work TASK-*`              | Full task context + hooks; one `Executor.execute_task` (or one step of a one-item batch).                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `onward work CHUNK-*`             | Collects **eligible ready tasks** for each **wave** (dependency order, `work.max_retries`, `work.sequential_by_default`, and `work.max_parallel_tasks`). When `max_parallel_tasks > 1`, up to N ready tasks run concurrently via `ThreadPoolExecutor`; `post_task_shell` and `post_task_markdown` hooks are serialized with a threading lock. `depends_on` edges are validated as a DAG before the loop starts (cycles or dangling refs abort). After all waves succeed, **`post_chunk_markdown`** runs. See [LIFECYCLE.md](LIFECYCLE.md). |
| `onward work PLAN-*`              | Walks chunks like **`onward work CHUNK-*`** (batch per chunk wave).                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `onward review-plan`              | One or more reviewer runs: default uses `review.double_review` + tiered models / `review.reviewers` matrix (per-slot model, optional `command` / `args`, ordered `fallback`). Use `--reviewer LABEL` for matching slots only.                                                                                                                                                                                                                                                                                                              |
| `onward split PLAN-*` / `CHUNK-*` | **Default:** `type: split` JSON on stdin; preflight like other executor-backed commands. **Override:** `--heuristic` — markdown-only (no executor). **Validation:** sizing/dependency checks; `--dry-run` / `--force`.                                                                                                                                                                                                                                                                                                                     |
| Markdown hooks                    | `post_task_markdown`, `post_chunk_markdown` (shell hooks are **not** the executor). Chunk/task shell hooks: `pre_chunk_shell`, `pre_task_shell`, `post_task_shell`.                                                                                                                                                                                                                                                                                                                                                                        |

If `executor.enabled` is false, executor-backed steps are skipped or fail with a clear message (shell hooks may still run).

## Model configuration (tiered)

`models` in `.onward.config.yaml` uses **tier keys**: `default`, `high`, `medium`, `low`, `split`, `review_1`, `review_2`. Empty or null tier values participate in **automatic fallback chains** (e.g. `low` → `medium` → `high` → `default`). Resolution helpers live in [`config.py`](../src/onward/config.py) (`resolve_model_for_tier`, `resolve_model_for_task`).

**Task model resolution (in order):**

1. Non-empty **`model`** in task frontmatter — used as-is.
2. **`complexity: high|medium|low`** — maps to that tier (with fallbacks).
3. Otherwise — **`default`** tier.

**Deprecated (still read; `onward doctor` warns):** `task_default` (prefer `medium` + effort), `split_default` (prefer `split`), `review_default` (prefer `review_1`).

## Local / no model call

| Feature                                                                      | Notes                                                                                                       |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `onward split PLAN-*` / `CHUNK-*`                                            | Only with **`--heuristic`:** derives candidate chunks/tasks from markdown sections and builds JSON locally. |
| `onward new`, `list`, `show`, `tree`, `report`, `next`, `progress`, `recent` | Filesystem + derived indexes.                                                                               |
| `onward complete` / `cancel` / `retry`                                       | Status transitions only; see [LIFECYCLE.md](LIFECYCLE.md).                                                  |
| `onward note`, `onward archive`                                              | File updates.                                                                                               |
| `onward doctor`                                                              | Config/workspace validation (including tier keys and legacy model warnings).                                |
| `onward sync`                                                                | Git operations; no LLM.                                                                                     |

The **`--model`** flag on split overrides the resolved **split** tier model (after CLI flag, `model_setting` still honors legacy `split_default` when `split` is empty — prefer **`models.split`** going forward). Resolved models are written into new chunk/task metadata for **future** `onward work`.

## Test / development overrides

| Mechanism              | Purpose                                                                                                                                         |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `TRAIN_SPLIT_RESPONSE` | If set, `onward split` uses this string as the JSON response **instead of** calling the executor (or heuristics) — tests and local experiments. |

## Lifecycle vs capabilities

Artifact status rules are **orthogonal** to model usage: see [LIFECYCLE.md](LIFECYCLE.md) for `work` / `complete` / `cancel` / `retry`.

## Archived: provider registry design

The old **multi-provider registry** YAML design was **not** implemented. See [archive/PROVIDER_REGISTRY.md](archive/PROVIDER_REGISTRY.md) for historical context on why the simpler executor-first approach was chosen.

### `review-plan` reviewer matrix (config)

When `review.reviewers` is a **non-empty** list, Onward ignores `double_review` for slot count and runs one pass per list entry. Each entry is a mapping:

| Field      | Required | Meaning                                                                                                                                               |
| ---------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `label`    | no       | Stable name for logs and `--reviewer` (default `reviewer-1`, `reviewer-2`, …).                                                                        |
| `model`    | yes      | Logical model (aliases like `sonnet` are resolved).                                                                                                   |
| `command`  | no       | Executor argv0 for this slot only; default is `executor.command`.                                                                                     |
| `args`     | no       | Extra argv for this slot (list); default `[]` if `command` is set, else `executor.args`.                                                              |
| `fallback` | no       | Ordered list of alternates: string = model only (inherits this slot’s `command` / `args`), or a mapping with `model` and optional `command` / `args`. |

On **preflight failure** or **non-zero executor exit**, Onward tries the next fallback and prints a single line with `fallback_reason=preflight_failed` or `fallback_reason=executor_failed` (stable for tooling).

Example (OpenClaw-style primary, global default executor fallback — adjust binaries to your machine):

```yaml
review:
  reviewers:
    - label: openclaw
      model: sonnet
      command: openclaw
      args: [run, model]
      fallback:
        - sonnet
    - label: claude-cli
      model: opus
      command: claude
      args: [--print]
```
