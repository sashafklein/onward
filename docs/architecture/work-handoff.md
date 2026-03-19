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
- `.runs/*.json`: immutable run metadata snapshots.
- `.runs/*.log`: raw executor output and progress stream.

## Handoff packet

For each task, Onward builds one packet and passes it to the executor:

- task frontmatter + body
- chunk summary (if available)
- plan summary (if available)
- normalized model name
- execution constraints (timeouts, retries, hooks)

## Model normalization

Add a forgiving alias resolver before executor launch.

Examples:

- `opus` -> `claude-opus-4-1`
- `sonnet` -> `claude-sonnet-4`
- `haiku` -> `claude-haiku-4`
- `gpt5`, `gpt-5` -> `gpt-5`

Resolution priority:

1. task-level model in frontmatter
2. chunk/plan defaults (optional in future)
3. config default model

## Ralph bridge

Keep the bridge narrow in v1:

- Build executor command from packet.
- Stream output to `.onward/runs/<run>.log`.
- Update `.ongoing.json` on lifecycle transitions.
- Write final run snapshot (`completed`/`failed`).

This gives parent agents reliable oversight without coupling Onward to Ralph internals.

## Parent-agent oversight surface

Parent agent operations should be file-based and cheap:

- `onward progress`: read `.ongoing.json` + active run summaries.
- `onward recent`: read most recent run snapshots.
- `onward show TASK-###`: include latest run pointers.

This keeps orchestration transparent and scriptable for OpenClaw-style overseers.

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
