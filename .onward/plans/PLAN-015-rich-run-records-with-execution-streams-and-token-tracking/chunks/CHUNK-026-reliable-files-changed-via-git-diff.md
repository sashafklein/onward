---
id: "CHUNK-026"
type: "chunk"
plan: "PLAN-015"
project: ""
title: "Reliable files_changed via git diff"
status: "open"
description: ""
priority: "medium"
model: "sonnet-latest"
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:40:00Z"
---

# Summary

Replaces the executor self-report approach for `files_changed` with a reliable
git-diff computation: capture `HEAD` before the executor runs, then diff `HEAD`
after hooks complete. The result is stored in `info-*.json` and is accurate
regardless of whether the executor reports anything.

# Scope

- Add a `compute_files_changed(root, before_sha)` helper in `src/onward/util.py`
- Capture `git rev-parse HEAD` as `before_sha` before the executor subprocess runs
- After hooks complete, call `compute_files_changed` and write the result to `info-*.json`
- Fallback: when the repo has no commits or `git` is unavailable, store an empty list without crashing

# Out of scope

- Staged/unstaged fallback for non-committing hooks (noted in plan but low priority)
- Surfacing `files_changed` in the CLI (CHUNK-028)

# Dependencies

- CHUNK-024 (provides the `info-*.json` path in `PreparedTaskRun`)

# Expected files/systems involved

- `src/onward/util.py` — new `compute_files_changed` helper
- `src/onward/execution.py` — `before_sha` capture and post-hook update of run JSON

# Completion criteria

- [ ] `files_changed` in `info-*.json` is a non-empty list for tasks that commit files
- [ ] Helper returns `[]` gracefully when git is unavailable or `before_sha` is empty
- [ ] No crash when the task makes no git commits

# Notes

`before_sha` must be captured after any pre-task hooks run (they might commit too) and before the executor subprocess is spawned.
