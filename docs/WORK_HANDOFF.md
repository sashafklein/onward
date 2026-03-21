# Work Handoff Design (v1)

This is the key design stance for passing work from parent agents to worker agents.

Artifact **status** transitions (`complete` / `cancel` / `retry` vs `work`) are specified in **[LIFECYCLE.md](LIFECYCLE.md)**. Which commands invoke the executor vs run locally is summarized in **[CAPABILITIES.md](CAPABILITIES.md)**.

## Decision

Use a file-backed run coordinator in Onward v1, not a long-running daemon.

Reasoning:

- It keeps behavior deterministic and debuggable.
- It aligns with markdown/git-native state.
- It avoids introducing process lifecycle complexity too early.
- It still supports oversight via `onward progress` and `onward recent`.

A daemon can be added later behind the same runtime files if needed.

## Runtime state layout

New runs are stored in per-task subdirectories:

```txt
.onward/
  ongoing.json
  runs/
    TASK-020/
      info-2026-03-21T00-30-00Z.json      ← run metadata (replaces RUN-*.json)
      summary-2026-03-21T00-30-00Z.log    ← hook output + errors (replaces RUN-*.log)
      output-2026-03-21T00-30-00Z.log     ← live executor stdout/stderr stream (new)
      info-2026-03-21T01-15-00Z.json      ← retry run
      summary-2026-03-21T01-15-00Z.log
      output-2026-03-21T01-15-00Z.log
    TASK-021/
      ...
    RUN-2026-03-20T22-27-57Z-TASK-060.json  ← legacy flat files (still readable)
    RUN-2026-03-20T22-27-57Z-TASK-060.log
```

- `.ongoing.json`: active run queue and current status for quick parent-agent visibility.
- `runs/TASK-XXX/info-*.json`: run metadata snapshot (**JSON**). Contains `status`, `model`, `executor`, `started_at`, `finished_at`, `files_changed`, and `token_usage`.
- `runs/TASK-XXX/summary-*.log`: post-hoc log written at completion — hook outputs, error messages, executor output summary.
- `runs/TASK-XXX/output-*.log`: raw executor stdout/stderr stream written in real-time during execution. You can `tail -f` this file from another terminal to monitor a running task:
  ```bash
  tail -f .onward/runs/TASK-020/output-*.log
  ```
- Legacy `RUN-<timestamp>-TASK-<id>.json` / `.log` files from older runs remain in the flat `runs/` directory and are still readable by all `onward` commands.
- Multiple runs per task (retries) each get their own timestamped triple inside the task directory.

### Example `info-*.json`

```json
{
  "id": "RUN-2026-03-21T00-30-00Z-TASK-020",
  "type": "run",
  "target": "TASK-020",
  "plan": "PLAN-005",
  "chunk": "CHUNK-010",
  "status": "completed",
  "model": "claude-sonnet-4-20250514",
  "executor": "builtin",
  "started_at": "2026-03-21T00:30:00Z",
  "finished_at": "2026-03-21T00:32:13Z",
  "log_path": ".onward/runs/TASK-020/summary-2026-03-21T00-30-00Z.log",
  "error": "",
  "files_changed": ["src/onward/execution.py", "tests/test_execution.py"],
  "token_usage": {
    "input_tokens": 12345,
    "output_tokens": 6789,
    "total_tokens": 19134
  }
}
```

`files_changed` is populated from `git diff` after post-task hooks run (not self-reported by the executor). `token_usage` is `null` when the executor does not provide it.

## Handoff packet

For each task, Onward builds a JSON packet and passes it via stdin to the executor. Every packet includes **`schema_version`** (currently **`1`**) so executors can branch on shape. Machine-readable schema: [`docs/schemas/onward-executor-stdin-v1.schema.json`](schemas/onward-executor-stdin-v1.schema.json). Custom tooling that replays older captures may omit that field — use `normalize_executor_stdin_payload()` (see [Format migration](FORMAT_MIGRATION.md)).

The task packet contains:

```json
{
  "type": "task",
  "schema_version": 1,
  "run_id": "RUN-<timestamp>-TASK-<id>",
  "task": { /* task frontmatter metadata */ },
  "body": "task markdown body",
  "notes": "accumulated scratch-pad notes (or null)",
  "notes_hint": "onward note <ID> usage hint",
  "chunk": {
    "metadata": { /* parent chunk frontmatter */ },
    "body": "chunk markdown body"
  },
  "plan": {
    "metadata": { /* parent plan frontmatter */ },
    "body": "plan markdown body"
  }
}
```

The `chunk` and `plan` fields give the executor full context about the parent scope — goals, constraints, acceptance criteria, and approach — without requiring it to read the filesystem.

## Model strings

**Tasks:** Onward resolves a concrete model string before invoking the executor: explicit **`model`** in task frontmatter wins; else **`effort: high|medium|low`** maps to the matching **`models`** tier (with automatic fallbacks); else the **`default`** tier. Tier keys are **`default`**, **`high`**, **`medium`**, **`low`**, **`split`**, **`review_1`**, **`review_2`** — see [CAPABILITIES.md](CAPABILITIES.md). Legacy flat keys **`task_default`**, **`split_default`**, and **`review_default`** are still read for compatibility but are **deprecated**; **`onward doctor`** warns — migrate to tiers.

**Split / flags:** `--model` on `onward split` overrides the resolved **split** tier model after CLI parsing.

**External subprocess executor:** Onward passes the resolved identifier **through unchanged** on stdin; your command maps aliases (e.g. `sonnet-latest`) to vendor IDs.

**Built-in executor:** The same string selects **Claude Code** vs **Cursor agent** via heuristics in code (`route_model_to_backend`); the CLI then interprets the model id.

## Hook execution

Hooks run at well-defined lifecycle points around task and chunk execution:

| Hook | Type | When |
|------|------|------|
| `pre_chunk_shell` | Shell command(s) | Once when `onward work CHUNK-*` starts, before any task in that chunk |
| `pre_task_shell` | Shell command(s) | Before each task execution |
| `post_task_shell` | Shell command(s) | After successful task execution |
| `post_task_markdown` | Markdown via executor | After successful task execution (after shell hooks) |
| `post_chunk_markdown` | Markdown via executor | After all tasks in a chunk complete successfully |

Shell hooks run as subprocess commands in the workspace root. Markdown hooks use the **stdin-JSON subprocess** shape (same idea as an external task executor): when the workspace **`executor.command`** is **`builtin`** or unset, Onward falls back to the reference **`onward-exec`** adapter so hooks still receive JSON on stdin. Any hook failure aborts execution and marks the run as failed.

**Examples:** `pre_task_shell: ["git stash"]` before each task; `post_task_shell: ["git add -A && git commit -m 'onward: task done' --allow-empty"]` after a successful task; `pre_chunk_shell` for one-time setup (e.g. ensure a service is up) before the chunk’s task loop.

### Environment variables for shell hooks

For **`pre_chunk_shell`**, Onward sets:

| Variable | Meaning |
| -------- | ------- |
| `ONWARD_CHUNK_ID` | Chunk id (e.g. `CHUNK-001`). |
| `ONWARD_CHUNK_TITLE` | Chunk `title` from frontmatter. |

For **`pre_task_shell`** and **`post_task_shell`**, Onward merges these into the subprocess environment (in addition to the normal process environment):

| Variable | Meaning |
| -------- | ------- |
| `ONWARD_RUN_ID` | Current run id (same as `run_id` in the stdin payload for the main task executor). |
| `ONWARD_TASK_ID` | Task id being executed (e.g. `TASK-001`). |
| `ONWARD_TASK_TITLE` | Task `title` from frontmatter. |

The main executor subprocess also receives **`ONWARD_RUN_ID`** (see below).

### Default `post_task_shell` commit hook

Fresh **`onward init`** workspaces ship with a default **`post_task_shell`** entry that stages and commits after each successful task:

```bash
git add -A && git commit -m 'onward: completed ${ONWARD_TASK_ID} - ${ONWARD_TASK_TITLE}' --allow-empty
```

`${ONWARD_TASK_ID}` and `${ONWARD_TASK_TITLE}` are expanded by the shell from the environment above. **`--allow-empty`** keeps the hook from failing when a task legitimately produces no file changes. To disable, set **`post_task_shell: []`** in `.onward.config.yaml`.

## Executor bridge

Task execution uses the **`Executor`** abstraction in Python (see **`onward.executor`**):

- **Default:** **`executor.command`** absent, empty, or **`builtin`** → **`BuiltinExecutor`** runs **Claude** or **Cursor** directly, streams output to the terminal, and builds prompts in Python.
- **Custom:** any other **`executor.command`** → **`SubprocessExecutor`** runs **`[command, *args]`** with the full handoff packet on **stdin** as JSON (same schema as before). The repo includes a reference router at **`scripts/onward-exec`** (stdin JSON → host CLI); you can still point **`executor.command`** at it or at your own tool.

For both paths:

- Set environment variable **`ONWARD_RUN_ID`** on the child process to the current run id (same value as `run_id` in the stdin payload for subprocess executors) so executors can echo it back in acknowledgments.
- Capture combined output to `.onward/runs/<run>.log` (built-in executor tees streams to your TTY while logging).
- Update `.ongoing.json` on lifecycle transitions (add on start, remove on finish).
- Write final run snapshot with `completed` or `failed` status.

Chunk work calls **`execute_batch`** per **wave** of ready tasks (sequential steps inside the batch); see [LIFECYCLE.md](LIFECYCLE.md).

### Task success acknowledgment (optional strict contract)

By default, a **successful** task run is **`exit code 0`** from the main executor subprocess (after hooks). For stricter **execution truthfulness**, set in `.onward.config.yaml`:

```yaml
work:
  require_success_ack: true
```

When **true**, exit code **0 alone is not enough**. The executor must also print a **single-line JSON object** (on stdout or stderr) that Onward can parse, containing a completed status. Onward scans **non-empty lines from bottom to top** in stdout, then stderr, and uses the **first** line that is valid JSON with an `onward_task_result` object.

Accepted schema versions: **`1`**, **`2`**, **`3`**. See [`schemas/onward-task-success-ack-v1.schema.json`](schemas/onward-task-success-ack-v1.schema.json).

Minimal example line (v1):

```json
{"onward_task_result":{"status":"completed","schema_version":1}}
```

Schema v3 adds an optional `token_usage` field:

```json
{
  "onward_task_result": {
    "schema_version": 3,
    "status": "completed",
    "run_id": "RUN-2026-03-21T00-30-00Z-TASK-020",
    "token_usage": {
      "input_tokens": 12345,
      "output_tokens": 6789
    }
  }
}
```

`token_usage` is optional — omitting it or setting it to `null` is valid. When provided, Onward stores it in `info-*.json` under the `token_usage` key.

If `onward_task_result.run_id` is present, it **must** equal `ONWARD_RUN_ID` (and the stdin `run_id`) or the run fails.

When an acknowledgment is present and valid, Onward stores the **parsed JSON object** on the run record under **`success_ack`** for auditing. Markdown hooks (`post_task_markdown`, `post_chunk_markdown`) and `onward review-plan` are **not** subject to this contract—only the **main task** executor invocation.

## Parent-agent oversight surface

All parent-agent operations are file-based and cheap:

- **`onward progress`**: reads `.ongoing.json` active runs plus all `in_progress` artifacts.
- **`onward recent`**: shows recently completed artifacts _and_ terminal run records (completed/failed) sorted by timestamp.
- **`onward show TASK-###`**: displays full artifact detail plus the latest run for that task (run ID, status, timestamps, log path, error if any).
- **`index.yaml`**: regenerated on every artifact write; includes a `runs` section summarizing all run records.

This keeps orchestration transparent and scriptable for overseer-style parent agents.

## Plan execution

`onward work PLAN-###` runs **`onward work CHUNK-*`** for each child chunk in plan order (skipping terminal chunks, respecting chunk **`depends_on`**), then completes the plan when all chunks succeed. See **[LIFECYCLE.md](LIFECYCLE.md)**.

## Chunk execution

`onward work CHUNK-###` executes tasks sequentially with dependency awareness, using **batch waves**:

1. Set chunk status to `in_progress`.
2. Run `pre_chunk_shell` hooks (once per `onward work CHUNK-*` invocation).
3. Collect **ready** open tasks belonging to the chunk (`depends_on` / legacy `blocked_by` must be **`completed`**).
4. Apply **`work.max_retries`** and **`work.sequential_by_default`** to form a **wave** of eligible tasks (when `sequential_by_default` is false, the wave is at most one task per invocation).
5. For that wave, call **`Executor.execute_batch`**: for each task in order, run `pre_task_shell`, the executor step, then post-task hooks on success.
6. Stop on first task failure in the wave.
7. Repeat from step 3 until no runnable tasks remain.
8. Run `post_chunk_markdown` hook after all tasks complete.
9. Mark chunk as `completed`.

Tasks blocked by unmet dependencies are reported but not executed. If no tasks are ready and blocked tasks remain, the chunk reports unresolved dependencies and exits with an error.

## Feedback loop policy

Workers should capture newly discovered work while executing a task, not defer it to memory.

Recommended default guidance:

- when a blocker/refactor/follow-up is discovered, create a new task artifact immediately
- default placement is the current chunk unless reassignment is clearly better
- include frontmatter metadata when known:
  - `blocked_by`
  - `human`
  - `project`

This keeps momentum high and prevents discovered work from being lost between agent runs.
