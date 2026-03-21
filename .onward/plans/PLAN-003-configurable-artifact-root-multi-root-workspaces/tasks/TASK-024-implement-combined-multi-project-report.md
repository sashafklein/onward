---
id: "TASK-024"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-006"
project: ""
title: "Implement combined multi-project report"
status: "completed"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "m"
depends_on:
- "TASK-023"
files: []
acceptance: []
created_at: "2026-03-21T15:49:39Z"
updated_at: "2026-03-21T17:56:27Z"
run_count: 1
last_run_status: "completed"
---

# Context

`onward report` and `onward next` are the primary status commands. In multi-root mode without `--project`, they should show a combined view across all projects rather than erroring.

# Scope

- In `cmd_report`: when multi-root and no `--project`, load artifacts from all roots and present a combined report.
  - Group report sections by project (add a project header or project column).
  - Show per-project summaries and an overall summary.
- In `cmd_next`: when multi-root and no `--project`, pick the next recommended task across all projects.
  - Display the project name alongside the task ID in the output.
- `--project` still works to scope to a single project.
- Adjust `cmd_report` and `cmd_next` to bypass the `require_project_or_default` error in multi-root mode (these are the exception to the "must specify project" rule).

# Out of scope

- Combined multi-project `onward list` or `onward tree` (can be added later).
- Markdown report output (PLAN-004 scope).
- Cross-project dependency resolution.

# Files to inspect

- `src/onward/cli_commands.py` — `cmd_report`, `cmd_next`
- `src/onward/artifacts.py` — `artifact_glob` (needs to scan all roots)

# Implementation notes

- Report output format: use project name as a section header, e.g. `## Project: frontend` followed by the normal report content for that project.
- For `cmd_next`, priority ordering should work the same way per-project; the combined view just merges the results.
- Consider whether `cmd_progress` and `cmd_ready` should also support combined views — if yes, add them here; if not, note as a follow-up.
- The combined report may be longer — consider a summary-first format.

# Acceptance criteria

- `onward report` in multi-root mode without `--project` shows all projects grouped by project name.
- `onward report --project frontend` shows only that project's report.
- `onward next` in multi-root mode picks across all projects and shows project context.
- Single-root mode behavior is unchanged.

# Handoff notes

- This is a UX-critical task — the combined report is how users see the big picture across projects.
- Consider adding `cmd_progress` and `cmd_ready` combined views as a follow-up if not included here.
