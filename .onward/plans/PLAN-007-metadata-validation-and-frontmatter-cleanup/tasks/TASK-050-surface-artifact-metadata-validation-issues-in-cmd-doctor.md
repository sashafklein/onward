---
id: "TASK-050"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-015"
project: ""
title: "Surface artifact metadata validation issues in cmd_doctor()"
status: "in_progress"
description: "In `src/onward/cli_commands.py`, update `cmd_doctor()` to validate artifact metadata across the workspace.\n\nAfter the existing per-project-root structure checks (directories, required files, ongoing.json), add a block that:\n1. Calls `collect_artifacts(layout, project_key)` (or `collect_artifacts(layout)` for single-root) to get all artifact objects under that project root\n2. For each artifact, calls `validate_artifact(artifact)` and collects returned issues\n3. Appends all issues to the existing `issues` list so they are printed and counted alongside structural issues\n\nMake sure `validate_artifact` is already imported (it is in the existing imports from `onward.artifacts`).\n\nThe doctor output format must list each metadata issue on its own line (the existing issues printing logic already handles this — just append to the list)."
human: false
model: "sonnet"
executor: "onward-exec"
depends_on:
- "TASK-048"
files:
- "src/onward/cli_commands.py"
acceptance:
- "`onward doctor` on a workspace containing a task with `complexity: banana` prints a line mentioning that task's path and the bad value"
- "The doctor exit code is non-zero when metadata issues are found"
- "The doctor exit code remains 0 and prints 'Doctor check passed' for a clean workspace with well-formed artifacts"
- "All existing doctor tests continue to pass"
created_at: "2026-03-21T20:20:59Z"
updated_at: "2026-03-21T20:37:25Z"
effort: "s"
run_count: 1
---

# Context

In `src/onward/cli_commands.py`, update `cmd_doctor()` to validate artifact metadata across the workspace.

After the existing per-project-root structure checks (directories, required files, ongoing.json), add a block that:
1. Calls `collect_artifacts(layout, project_key)` (or `collect_artifacts(layout)` for single-root) to get all artifact objects under that project root
2. For each artifact, calls `validate_artifact(artifact)` and collects returned issues
3. Appends all issues to the existing `issues` list so they are printed and counted alongside structural issues

Make sure `validate_artifact` is already imported (it is in the existing imports from `onward.artifacts`).

The doctor output format must list each metadata issue on its own line (the existing issues printing logic already handles this — just append to the list).

# Scope

- In `src/onward/cli_commands.py`, update `cmd_doctor()` to validate artifact metadata across the workspace.

After the existing per-project-root structure checks (directories, required files, ongoing.json), add a block that:
1. Calls `collect_artifacts(layout, project_key)` (or `collect_artifacts(layout)` for single-root) to get all artifact objects under that project root
2. For each artifact, calls `validate_artifact(artifact)` and collects returned issues
3. Appends all issues to the existing `issues` list so they are printed and counted alongside structural issues

Make sure `validate_artifact` is already imported (it is in the existing imports from `onward.artifacts`).

The doctor output format must list each metadata issue on its own line (the existing issues printing logic already handles this — just append to the list).

# Out of scope

- None specified.

# Files to inspect

- `src/onward/cli_commands.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- `onward doctor` on a workspace containing a task with `complexity: banana` prints a line mentioning that task's path and the bad value
- The doctor exit code is non-zero when metadata issues are found
- The doctor exit code remains 0 and prints 'Doctor check passed' for a clean workspace with well-formed artifacts
- All existing doctor tests continue to pass

# Handoff notes
