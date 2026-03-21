---
id: "TASK-089"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-026"
project: ""
title: "Capture before_sha and populate files_changed in run JSON"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: ["TASK-084", "TASK-088"]
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:40:00Z"
---

# Context

With the helpers from TASK-088 ready and the new `info-*.json` path from TASK-084,
this task integrates them into the execution flow in `execution.py`.

# Scope

- Before spawning the executor subprocess (after pre-task hooks), call `get_head_sha(root)` and store as `before_sha`
- After post-task hooks complete, call `compute_files_changed(root, before_sha)`
- Update the `info-*.json` (run_json) with the resulting list in the `files_changed` key
- If the run JSON was already written with a placeholder, re-read and update it; otherwise include it in the final write

# Out of scope

- Staged/unstaged fallback (deferred per plan)
- Displaying `files_changed` in the CLI (CHUNK-028)

# Files to inspect

- `src/onward/execution.py` — `_run_hooked_executor_batch` and the point where `run_json` is written/updated

# Implementation notes

- Capture `before_sha` after `pre_task_shell` hooks run but before executor is called — hooks sometimes do `git add` or `git commit` themselves
- Use `json` module to read and update the existing JSON rather than overwriting wholesale
- If `before_sha` is `""` (e.g., repo has no commits), store `files_changed: []` and continue

# Acceptance criteria

- [ ] `info-*.json` contains `"files_changed": ["src/...", ...]` after a task that commits
- [ ] `"files_changed": []` when the task makes no git commits
- [ ] No crash when `git` is not available in PATH
- [ ] Integration test: create a tmp git repo, run a task that modifies a file, assert `files_changed` is populated

# Handoff notes

After this task, `files_changed` is reliable. CHUNK-028 surfaces it in `onward show`.
