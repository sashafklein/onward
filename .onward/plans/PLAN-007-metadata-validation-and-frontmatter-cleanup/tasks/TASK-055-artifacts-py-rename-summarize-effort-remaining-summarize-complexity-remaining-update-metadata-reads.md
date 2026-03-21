---
id: "TASK-055"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-016"
project: ""
title: "artifacts.py: rename summarize_effort_remaining → summarize_complexity_remaining, update metadata reads"
status: "open"
description: "In `src/onward/artifacts.py`:\n\n1. Rename `summarize_effort_remaining` to `summarize_complexity_remaining` (function definition at ~line 304).\n2. Change the counts dict from `{\"xs\": 0, \"s\": 0, \"m\": 0, \"l\": 0, \"xl\": 0, \"unestimated\": 0}` to `{\"low\": 0, \"medium\": 0, \"high\": 0, \"unestimated\": 0}`.\n3. Change the metadata read on ~line 312 from `a.metadata.get(\"effort\", \"\")` to `a.metadata.get(\"complexity\", \"\")`. Update the valid set from `{\"xs\", \"s\", \"m\", \"l\", \"xl\"}` to `{\"low\", \"medium\", \"high\"}`.\n4. In the batch row builder (~lines 635-647 and ~783-798), rename the metadata key reads/writes from `\"effort\"` to `\"complexity\"`. These are in two symmetric blocks — one for chunks and one for tasks.\n5. In ~line 1056, update `task.metadata.get(\"effort\", \"\")` to `task.metadata.get(\"complexity\", \"\")`.\n\nDo not add a compat fallback to `effort` in this function — the model resolution compat lives in config.py only."
human: false
model: "sonnet"
executor: "onward-exec"
depends_on:
- "TASK-053"
files:
- "src/onward/artifacts.py"
acceptance:
- "summarize_complexity_remaining is the new function name; summarize_effort_remaining is gone"
- "summarize_complexity_remaining returns dict with keys 'low', 'medium', 'high', 'unestimated'"
- "Tasks with complexity: high increment counts['high']"
- "Tasks with complexity: xl (invalid) increment counts['unestimated']"
- "Tasks with no complexity key increment counts['unestimated']"
- "Batch row builders write 'complexity' key not 'effort'"
- "Zero grep matches for summarize_effort_remaining in artifacts.py"
created_at: "2026-03-21T20:23:52Z"
updated_at: "2026-03-21T20:23:52Z"
effort: "s"
---

# Context

In `src/onward/artifacts.py`:

1. Rename `summarize_effort_remaining` to `summarize_complexity_remaining` (function definition at ~line 304).
2. Change the counts dict from `{"xs": 0, "s": 0, "m": 0, "l": 0, "xl": 0, "unestimated": 0}` to `{"low": 0, "medium": 0, "high": 0, "unestimated": 0}`.
3. Change the metadata read on ~line 312 from `a.metadata.get("effort", "")` to `a.metadata.get("complexity", "")`. Update the valid set from `{"xs", "s", "m", "l", "xl"}` to `{"low", "medium", "high"}`.
4. In the batch row builder (~lines 635-647 and ~783-798), rename the metadata key reads/writes from `"effort"` to `"complexity"`. These are in two symmetric blocks — one for chunks and one for tasks.
5. In ~line 1056, update `task.metadata.get("effort", "")` to `task.metadata.get("complexity", "")`.

Do not add a compat fallback to `effort` in this function — the model resolution compat lives in config.py only.

# Scope

- In `src/onward/artifacts.py`:

1. Rename `summarize_effort_remaining` to `summarize_complexity_remaining` (function definition at ~line 304).
2. Change the counts dict from `{"xs": 0, "s": 0, "m": 0, "l": 0, "xl": 0, "unestimated": 0}` to `{"low": 0, "medium": 0, "high": 0, "unestimated": 0}`.
3. Change the metadata read on ~line 312 from `a.metadata.get("effort", "")` to `a.metadata.get("complexity", "")`. Update the valid set from `{"xs", "s", "m", "l", "xl"}` to `{"low", "medium", "high"}`.
4. In the batch row builder (~lines 635-647 and ~783-798), rename the metadata key reads/writes from `"effort"` to `"complexity"`. These are in two symmetric blocks — one for chunks and one for tasks.
5. In ~line 1056, update `task.metadata.get("effort", "")` to `task.metadata.get("complexity", "")`.

Do not add a compat fallback to `effort` in this function — the model resolution compat lives in config.py only.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/artifacts.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- summarize_complexity_remaining is the new function name; summarize_effort_remaining is gone
- summarize_complexity_remaining returns dict with keys 'low', 'medium', 'high', 'unestimated'
- Tasks with complexity: high increment counts['high']
- Tasks with complexity: xl (invalid) increment counts['unestimated']
- Tasks with no complexity key increment counts['unestimated']
- Batch row builders write 'complexity' key not 'effort'
- Zero grep matches for summarize_effort_remaining in artifacts.py

# Handoff notes
