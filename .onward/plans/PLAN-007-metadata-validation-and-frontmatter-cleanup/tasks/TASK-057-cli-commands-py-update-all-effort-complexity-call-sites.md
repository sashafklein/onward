---
id: "TASK-057"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-016"
project: ""
title: "cli_commands.py: update all effort→complexity call sites"
status: "open"
description: "In `src/onward/cli_commands.py`, make the following changes:\n\n**Imports (~lines 40, 108):**\n- Change `summarize_effort_remaining` import to `summarize_complexity_remaining`\n- Change `normalize_effort` import to `normalize_complexity`\n\n**cmd_new_chunk (~lines 691-697):**\n- Change `getattr(args, 'effort', None)` → `getattr(args, 'complexity', None)`\n- Change `normalize_effort(raw_eff)` → `normalize_complexity(raw_eff)` (also rename variable from `raw_eff` to `raw_cpx` for clarity, or just update the normalize call)\n- Change `metadata['effort'] = eff` → `metadata['complexity'] = cpx`\n- Change warning message from `\"expected xs|s|m|l|xl\"` to `\"expected low|medium|high\"`\n\n**cmd_new_task_batch (~line 820):**\n- Change `normalize_effort(entry.get('effort', ''))` → `normalize_complexity(entry.get('complexity', ''))` \n- Change `metadata['effort'] = eff` → `metadata['complexity'] = cpx`\n\n**cmd_new_task (~lines 896-902):**\n- Change `getattr(args, 'effort', None)` → `getattr(args, 'complexity', None)`\n- Change `normalize_effort(raw_eff)` → `normalize_complexity(raw_cpx)`\n- Change `metadata['effort'] = eff` → `metadata['complexity'] = cpx`\n- Change warning message from `\"expected xs|s|m|l|xl\"` to `\"expected low|medium|high\"`\n\n**cmd_show (~lines 1153-1155):**\n- Change `artifact.metadata.get('effort', '')` → `artifact.metadata.get('complexity', '')`\n- Change `print(f'effort: {eff}')` → `print(f'complexity: {cpx}')`\n\n**Lines ~1784, ~1862, ~2077, ~2081, ~2098, ~2200 (effort display in ready/report/tree):**\n- Change `task.metadata.get('effort', '')` → `task.metadata.get('complexity', '')`\n- Change all `summarize_effort_remaining(...)` calls → `summarize_complexity_remaining(...)`\n- Update any f-string labels from `effort` to `complexity`"
human: false
model: "sonnet"
executor: "onward-exec"
depends_on:
- "TASK-053"
- "TASK-055"
- "TASK-056"
files:
- "src/onward/cli_commands.py"
acceptance:
- "normalize_complexity is imported instead of normalize_effort"
- "summarize_complexity_remaining is imported instead of summarize_effort_remaining"
- "args.complexity is read instead of args.effort in cmd_new_chunk and cmd_new_task"
- "metadata['complexity'] is written instead of metadata['effort']"
- "Warning messages reference low|medium|high not xs|s|m|l|xl"
- "cmd_show prints 'complexity: X' not 'effort: X' when the key is set"
- "Zero grep matches for normalize_effort or summarize_effort_remaining in cli_commands.py"
- "Zero grep matches for args.effort or metadata\\[.effort. in cli_commands.py"
created_at: "2026-03-21T20:23:52Z"
updated_at: "2026-03-21T20:23:52Z"
effort: "s"
---

# Context

In `src/onward/cli_commands.py`, make the following changes:

**Imports (~lines 40, 108):**
- Change `summarize_effort_remaining` import to `summarize_complexity_remaining`
- Change `normalize_effort` import to `normalize_complexity`

**cmd_new_chunk (~lines 691-697):**
- Change `getattr(args, 'effort', None)` → `getattr(args, 'complexity', None)`
- Change `normalize_effort(raw_eff)` → `normalize_complexity(raw_eff)` (also rename variable from `raw_eff` to `raw_cpx` for clarity, or just update the normalize call)
- Change `metadata['effort'] = eff` → `metadata['complexity'] = cpx`
- Change warning message from `"expected xs|s|m|l|xl"` to `"expected low|medium|high"`

**cmd_new_task_batch (~line 820):**
- Change `normalize_effort(entry.get('effort', ''))` → `normalize_complexity(entry.get('complexity', ''))` 
- Change `metadata['effort'] = eff` → `metadata['complexity'] = cpx`

**cmd_new_task (~lines 896-902):**
- Change `getattr(args, 'effort', None)` → `getattr(args, 'complexity', None)`
- Change `normalize_effort(raw_eff)` → `normalize_complexity(raw_cpx)`
- Change `metadata['effort'] = eff` → `metadata['complexity'] = cpx`
- Change warning message from `"expected xs|s|m|l|xl"` to `"expected low|medium|high"`

**cmd_show (~lines 1153-1155):**
- Change `artifact.metadata.get('effort', '')` → `artifact.metadata.get('complexity', '')`
- Change `print(f'effort: {eff}')` → `print(f'complexity: {cpx}')`

**Lines ~1784, ~1862, ~2077, ~2081, ~2098, ~2200 (effort display in ready/report/tree):**
- Change `task.metadata.get('effort', '')` → `task.metadata.get('complexity', '')`
- Change all `summarize_effort_remaining(...)` calls → `summarize_complexity_remaining(...)`
- Update any f-string labels from `effort` to `complexity`

# Scope

- In `src/onward/cli_commands.py`, make the following changes:

**Imports (~lines 40, 108):**
- Change `summarize_effort_remaining` import to `summarize_complexity_remaining`
- Change `normalize_effort` import to `normalize_complexity`

**cmd_new_chunk (~lines 691-697):**
- Change `getattr(args, 'effort', None)` → `getattr(args, 'complexity', None)`
- Change `normalize_effort(raw_eff)` → `normalize_complexity(raw_eff)` (also rename variable from `raw_eff` to `raw_cpx` for clarity, or just update the normalize call)
- Change `metadata['effort'] = eff` → `metadata['complexity'] = cpx`
- Change warning message from `"expected xs|s|m|l|xl"` to `"expected low|medium|high"`

**cmd_new_task_batch (~line 820):**
- Change `normalize_effort(entry.get('effort', ''))` → `normalize_complexity(entry.get('complexity', ''))` 
- Change `metadata['effort'] = eff` → `metadata['complexity'] = cpx`

**cmd_new_task (~lines 896-902):**
- Change `getattr(args, 'effort', None)` → `getattr(args, 'complexity', None)`
- Change `normalize_effort(raw_eff)` → `normalize_complexity(raw_cpx)`
- Change `metadata['effort'] = eff` → `metadata['complexity'] = cpx`
- Change warning message from `"expected xs|s|m|l|xl"` to `"expected low|medium|high"`

**cmd_show (~lines 1153-1155):**
- Change `artifact.metadata.get('effort', '')` → `artifact.metadata.get('complexity', '')`
- Change `print(f'effort: {eff}')` → `print(f'complexity: {cpx}')`

**Lines ~1784, ~1862, ~2077, ~2081, ~2098, ~2200 (effort display in ready/report/tree):**
- Change `task.metadata.get('effort', '')` → `task.metadata.get('complexity', '')`
- Change all `summarize_effort_remaining(...)` calls → `summarize_complexity_remaining(...)`
- Update any f-string labels from `effort` to `complexity`

# Out of scope

- None specified.

# Files to inspect

- `src/onward/cli_commands.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- normalize_complexity is imported instead of normalize_effort
- summarize_complexity_remaining is imported instead of summarize_effort_remaining
- args.complexity is read instead of args.effort in cmd_new_chunk and cmd_new_task
- metadata['complexity'] is written instead of metadata['effort']
- Warning messages reference low|medium|high not xs|s|m|l|xl
- cmd_show prints 'complexity: X' not 'effort: X' when the key is set
- Zero grep matches for normalize_effort or summarize_effort_remaining in cli_commands.py
- Zero grep matches for args.effort or metadata\[.effort. in cli_commands.py

# Handoff notes
