# Work Handoff Design (v1)

This is the key design stance for passing work from parent agents to worker agents.

## Decision

Use a file-backed run coordinator in Onward v1, not a long-running daemon.

Reasoning:

- It keeps behavior deterministic and debuggable.
- It aligns with markdown/git-native state.
- It avoids introducing process lifecycle complexity too early.
- It still supports oversight via `onward progress` and `onward recent`.

A daemon can be added later behind the same runtime files if needed.

## Runtime state layout

```txt
.onward/
  ongoing.json
  runs/
    RUN-<timestamp>-TASK-<id>.json
    RUN-<timestamp>-TASK-<id>.log
```

- `.ongoing.json`: active run queue and current status for quick parent-agent visibility.
- `.runs/*.json`: immutable run metadata snapshots (YAML format).
- `.runs/*.log`: raw executor output including hook phases and progress stream.

## Handoff packet

For each task, Onward builds a JSON packet and passes it via stdin to the executor. The packet contains:

```json
{
  "type": "task",
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

## Model normalization

A forgiving alias resolver runs before executor launch.

Examples:

- `opus-latest` or `opus` -> `claude-opus-4-6`
- `sonnet-latest` or `sonnet` -> `claude-sonnet-4-6`
- `haiku-latest` or `haiku` -> `claude-haiku-4`
- `codex-latest` or `codex` -> `codex-5-3`
- `gpt5` -> `gpt-5`

Resolution priority:

1. task-level model in frontmatter
2. `--model` flag (for split/review commands)
3. config section models (`task_default`, `split_default`, `review_default`)
4. config `models.default`

## Hook execution

Hooks run at well-defined lifecycle points around task and chunk execution:

| Hook | Type | When |
|------|------|------|
| `pre_task_shell` | Shell command(s) | Before each task execution |
| `pre_task_markdown` | Markdown via executor | Before each task execution (after shell hooks) |
| `post_task_shell` | Shell command(s) | After successful task execution |
| `post_task_markdown` | Markdown via executor | After successful task execution (after shell hooks) |
| `post_chunk_markdown` | Markdown via executor | After all tasks in a chunk complete successfully |

Shell hooks run as subprocess commands in the workspace root. Markdown hooks are passed through the executor (Ralph) with a JSON payload containing the hook body, phase, model, and task/chunk metadata. Any hook failure aborts execution and marks the run as failed.

## Ralph bridge

The bridge stays narrow in v1:

- Build executor command from config (`ralph.command` + `ralph.args`).
- Pass the full handoff packet via stdin as JSON.
- Capture stdout/stderr to `.onward/runs/<run>.log`.
- Update `.ongoing.json` on lifecycle transitions (add on start, remove on finish).
- Write final run snapshot with `completed` or `failed` status.

This gives parent agents reliable oversight without coupling Onward to Ralph internals.

## Parent-agent oversight surface

All parent-agent operations are file-based and cheap:

- **`onward progress`**: reads `.ongoing.json` active runs plus all `in_progress` artifacts.
- **`onward recent`**: shows recently completed artifacts _and_ terminal run records (completed/failed) sorted by timestamp.
- **`onward show TASK-###`**: displays full artifact detail plus the latest run for that task (run ID, status, timestamps, log path, error if any).
- **`index.yaml`**: regenerated on every artifact write; includes a `runs` section summarizing all run records.

This keeps orchestration transparent and scriptable for overseer-style parent agents.

## Chunk execution

`onward work CHUNK-###` executes tasks sequentially with dependency awareness:

1. Set chunk status to `in_progress`.
2. Collect open tasks belonging to the chunk.
3. Check `depends_on` for each task; skip tasks whose dependencies aren't completed.
4. Execute ready tasks one at a time via the full task lifecycle (hooks + executor).
5. Stop on first task failure.
6. Run `post_chunk_markdown` hook after all tasks complete.
7. Mark chunk as `completed`.

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
