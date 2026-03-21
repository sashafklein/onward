---
id: "TASK-021"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-005"
project: ""
title: "Migrate split.py and cli_commands.py path references"
status: "in_progress"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "m"
depends_on:
- "TASK-018"
- "TASK-019"
- "TASK-020"
files: []
acceptance: []
created_at: "2026-03-21T15:49:32Z"
updated_at: "2026-03-21T17:21:42Z"
run_count: 1
---

# Context

After TASK-018/019/020 migrate the core modules, the remaining `.onward/` path literals live in `split.py` (prompt path) and `cli_commands.py` (plan dir, archive dir, prompt paths in various command handlers). This task cleans up those references.

# Scope

- In `split.py`: replace the hardcoded prompt path in `run_split_model` with `layout.prompts_dir(project)`.
- In `cli_commands.py`: replace the following hardcoded paths:
  - `plan_dir` in `cmd_new_plan` → `layout.plans_dir(project)`
  - `archive_dir` in `cmd_archive` → `layout.archive_dir(project)`
  - Prompt paths in `cmd_review_plan` and `cmd_split` display → `layout.prompts_dir(project)`
  - Any other `.onward/` references in command handlers
- Thread `layout` into these command handlers — construct it once from config at command entry, pass to called functions.
- Update function call sites that changed signatures in TASK-018/019/020.

# Out of scope

- Sync-related paths in cli_commands.py (TASK-026/027 handle those).
- The `require_project_or_default` helper (TASK-023).
- Multi-project report logic (TASK-024).

# Files to inspect

- `src/onward/split.py` — `run_split_model` and any `.onward` references
- `src/onward/cli_commands.py` — `cmd_new_plan`, `cmd_archive`, `cmd_review_plan`, `cmd_split`, and other handlers with `.onward` paths

# Implementation notes

- `cli_commands.py` is the largest file and has many command handlers. Build the `WorkspaceLayout` once in each handler (or in a shared helper) and pass it down.
- `split.py` is smaller — likely just one or two path references.
- After this task, a grep for `.onward/` in both files should return zero hits (except sync-related which are CHUNK-007 scope).
- Be careful not to break the argument threading — many handlers pass `root` to functions that now need `layout`.

# Acceptance criteria

- No `.onward/` path literals remain in `split.py` (except comments/docs).
- No `.onward/` path literals remain in `cli_commands.py` (except sync-related paths and the config file path `.onward.config.yaml`).
- All command handlers construct or receive a `WorkspaceLayout` and use it for path resolution.
- Existing tests pass.

# Handoff notes

- This task has the most dependencies (018, 019, 020) and should be done after all three. It's essentially the "wiring" task that connects the migrated modules to the CLI layer.
- TASK-023 builds on this to add `--project` argument handling.
