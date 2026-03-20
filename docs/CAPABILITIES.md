# Capability truth table

Short reference for **what is model-backed**, what is **local/heuristic**, and what exists only for **tests**. Keeps docs and mental models aligned with `src/onward/` (PLAN-010).

## Executor-backed (subprocess + stdin JSON)

These invoke the command from `ralph.command` (and `ralph.args`) when `ralph.enabled` is true, subject to each command’s checks:

**Strict task completion:** when `work.require_success_ack` is true, a successful **`onward work TASK-*`** requires a machine-readable JSON line on executor stdout/stderr (not exit 0 alone); see [WORK_HANDOFF.md](WORK_HANDOFF.md) and [schemas/onward-task-success-ack-v1.schema.json](schemas/onward-task-success-ack-v1.schema.json). The executor receives **`ONWARD_RUN_ID`** in its environment (matches stdin `run_id`).

**Preflight:** before the first executor subprocess for `onward work`, `onward review-plan`, and `post_chunk_markdown`, Onward checks that the configured command is usable: a **bare name** must resolve via `PATH` (`shutil.which`); an **explicit path** must exist and be executable. Commands `true` and `false` skip the check so tests and minimal shells work without a real provider binary (including environments where `/usr/bin/true` is not how tests are configured). See [`preflight_ralph_command`](../src/onward/preflight.py).

| Feature | Notes |
| ------- | ----- |
| `onward work TASK-*` | Full task payload + hooks; see [WORK_HANDOFF.md](WORK_HANDOFF.md). |
| `onward work CHUNK-*` | Same per ready task; `post_chunk_markdown` hook after all tasks succeed. |
| `onward review-plan` | One or more reviewer runs: default uses `review.double_review` + `models.review_default` / `models.default`, or an explicit matrix in `review.reviewers` (per-slot model, optional `command` / `args`, ordered `fallback`). Use `--reviewer LABEL` to run matching slots only (exact label). |
| Markdown hooks | `pre_task_markdown`, `post_task_markdown`, `post_chunk_markdown` (shell hooks are **not** the executor). |

If `ralph.enabled` is false, executor-backed steps are skipped or fail with a clear message (shell hooks may still run).

## Local / no model call

| Feature | Notes |
| ------- | ----- |
| `onward split PLAN-*` / `CHUNK-*` | **Heuristic only today:** derives candidate chunks/tasks from markdown sections (e.g. Goals, Scope, Completion criteria) and builds JSON locally. Does **not** call the executor or an external model in the default code path — **no executor preflight** on `split`. |
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

## Multi-provider routing (future)

A design for optional **provider registry** routing (multiple CLIs/backends) lives in [PROVIDER_REGISTRY.md](PROVIDER_REGISTRY.md). Until implemented and enabled in config, behavior remains **single executor** (`ralph`) plus `resolve_model_alias`.

### `review-plan` reviewer matrix (config)

When `review.reviewers` is a **non-empty** list, Onward ignores `double_review` for slot count and runs one pass per list entry. Each entry is a mapping:

| Field | Required | Meaning |
| ----- | -------- | ------- |
| `label` | no | Stable name for logs and `--reviewer` (default `reviewer-1`, `reviewer-2`, …). |
| `model` | yes | Logical model (aliases like `sonnet-latest` are resolved). |
| `command` | no | Executor argv0 for this slot only; default is `ralph.command`. |
| `args` | no | Extra argv for this slot (list); default `[]` if `command` is set, else `ralph.args`. |
| `fallback` | no | Ordered list of alternates: string = model only (inherits this slot’s `command` / `args`), or a mapping with `model` and optional `command` / `args`. |

On **preflight failure** or **non-zero executor exit**, Onward tries the next fallback and prints a single line with `fallback_reason=preflight_failed` or `fallback_reason=executor_failed` (stable for tooling).

Example (OpenClaw-style primary, global `ralph` fallback — adjust binaries to your machine):

```yaml
review:
  reviewers:
    - label: openclaw
      model: sonnet-latest
      command: openclaw
      args: [run, model]
      fallback:
        - sonnet-latest
    - label: claude-cli
      model: opus-latest
      command: claude
      args: [--print]
```
