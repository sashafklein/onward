---
id: "TASK-053"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-016"
project: ""
title: "util.py: rename normalize_effort → normalize_complexity, accept low|medium|high"
status: "in_progress"
description: "In `src/onward/util.py`:\n1. Rename `_normalize_effort` to `_normalize_complexity`. Change the accepted value set from `{\"xs\", \"s\", \"m\", \"l\", \"xl\"}` to `{\"low\", \"medium\", \"high\"}`.\n2. At the bottom of the file (public aliases section), replace `normalize_effort = _normalize_effort` with `normalize_complexity = _normalize_complexity`. Remove the old `normalize_effort` alias entirely — callers in split.py, cli_commands.py will be updated in their own tasks.\n\nThe new function signature is unchanged: `_normalize_complexity(value: Any) -> str` — returns the canonical string if valid, else `\"\"`.\n\nExample: `normalize_complexity('high') == 'high'`, `normalize_complexity('xl') == ''`, `normalize_complexity('') == ''`."
human: false
model: "haiku"
executor: "onward-exec"
depends_on: []
files:
- "src/onward/util.py"
acceptance:
- "normalize_complexity('low') returns 'low'"
- "normalize_complexity('medium') returns 'medium'"
- "normalize_complexity('high') returns 'high'"
- "normalize_complexity('HIGH') returns 'high' (case-insensitive via lower())"
- "normalize_complexity('xl') returns ''"
- "normalize_complexity('s') returns ''"
- "normalize_complexity is exported from util.py; normalize_effort is removed"
- "Zero grep matches for normalize_effort in src/onward/util.py"
created_at: "2026-03-21T20:23:52Z"
updated_at: "2026-03-21T20:51:33Z"
effort: "xs"
run_count: 1
---

# Context

In `src/onward/util.py`:
1. Rename `_normalize_effort` to `_normalize_complexity`. Change the accepted value set from `{"xs", "s", "m", "l", "xl"}` to `{"low", "medium", "high"}`.
2. At the bottom of the file (public aliases section), replace `normalize_effort = _normalize_effort` with `normalize_complexity = _normalize_complexity`. Remove the old `normalize_effort` alias entirely — callers in split.py, cli_commands.py will be updated in their own tasks.

The new function signature is unchanged: `_normalize_complexity(value: Any) -> str` — returns the canonical string if valid, else `""`.

Example: `normalize_complexity('high') == 'high'`, `normalize_complexity('xl') == ''`, `normalize_complexity('') == ''`.

# Scope

- In `src/onward/util.py`:
1. Rename `_normalize_effort` to `_normalize_complexity`. Change the accepted value set from `{"xs", "s", "m", "l", "xl"}` to `{"low", "medium", "high"}`.
2. At the bottom of the file (public aliases section), replace `normalize_effort = _normalize_effort` with `normalize_complexity = _normalize_complexity`. Remove the old `normalize_effort` alias entirely — callers in split.py, cli_commands.py will be updated in their own tasks.

The new function signature is unchanged: `_normalize_complexity(value: Any) -> str` — returns the canonical string if valid, else `""`.

Example: `normalize_complexity('high') == 'high'`, `normalize_complexity('xl') == ''`, `normalize_complexity('') == ''`.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/util.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- normalize_complexity('low') returns 'low'
- normalize_complexity('medium') returns 'medium'
- normalize_complexity('high') returns 'high'
- normalize_complexity('HIGH') returns 'high' (case-insensitive via lower())
- normalize_complexity('xl') returns ''
- normalize_complexity('s') returns ''
- normalize_complexity is exported from util.py; normalize_effort is removed
- Zero grep matches for normalize_effort in src/onward/util.py

# Handoff notes
