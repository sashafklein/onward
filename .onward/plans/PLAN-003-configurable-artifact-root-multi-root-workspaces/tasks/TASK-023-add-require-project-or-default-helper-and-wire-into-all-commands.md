---
id: "TASK-023"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-006"
project: ""
title: "Add require_project_or_default helper and wire into all commands"
status: "completed"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "l"
depends_on:
- "TASK-021"
files: []
acceptance: []
created_at: "2026-03-21T15:49:38Z"
updated_at: "2026-03-21T17:51:51Z"
run_count: 1
last_run_status: "completed"
---

# Context

When `roots` is configured, every artifact-touching command needs to know which project to operate on. This task creates a centralized helper and wires it into every command handler so multi-root mode works end-to-end.

# Scope

- Create `require_project_or_default(args, layout) -> str | None` helper function (in cli_commands.py or a shared utils module):
  - If single-root: return `None` (current behavior, no project distinction).
  - If multi-root with `--project` arg: return that project key (validate it exists in layout).
  - If multi-root with `default_project` config and no `--project`: return `default_project`.
  - If multi-root with no `--project` and no `default_project`: raise a clear error telling the user to pass `--project` or set `default_project` in config.
- Add `--project` argument to the CLI parser for all artifact-touching subcommands.
- Wire the helper into every command handler that touches artifacts:
  - `cmd_new_plan`, `cmd_new_chunk`, `cmd_new_task`, `cmd_new_task_batch`
  - `cmd_list`, `cmd_show`, `cmd_tree`
  - `cmd_work`, `cmd_complete`, `cmd_cancel`, `cmd_retry`
  - `cmd_next`, `cmd_report`, `cmd_progress`, `cmd_recent`, `cmd_ready`
  - `cmd_split`, `cmd_review_plan`, `cmd_archive`, `cmd_note`

# Out of scope

- Sync subcommands (TASK-027 adds `--project` to sync).
- Combined multi-project report (TASK-024 — special-cases report/next without `--project`).

# Files to inspect

- `src/onward/cli.py` — argument parser definitions for all subcommands
- `src/onward/cli_commands.py` — all `cmd_*` handler functions

# Implementation notes

- `--project` should be optional in single-root mode (ignored/unused).
- The parser argument can be added to a parent parser that all subcommands inherit, or added individually to each subcommand.
- Use `add_argument("--project", default=None)` — the helper resolves the default.
- In single-root mode, `require_project_or_default` returns `None` and callers pass `project=None` to layout methods — maintaining backward compatibility.
- Error message example: `"Multiple project roots configured. Use --project <name> or set default_project in .onward.config.yaml. Available projects: a, b"`.

# Acceptance criteria

- `--project` argument available on all artifact-touching commands.
- In single-root mode, commands work exactly as before (no `--project` needed).
- In multi-root mode with `default_project` set, commands work without `--project`.
- In multi-root mode without `default_project` and without `--project`, a clear error is raised.
- Invalid `--project` value produces a clear error listing available projects.

# Handoff notes

- This is a high-touch task — it modifies every command handler. Run the full test suite after to catch any missed handlers.
- TASK-024 builds on this for the special case of `report`/`next` showing all projects.
