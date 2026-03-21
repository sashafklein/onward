---
id: "TASK-071"
type: "task"
plan: "PLAN-013"
chunk: "CHUNK-020"
project: ""
title: "Add claimed_ids filtering to report_rows and select_next_artifact"
status: "completed"
description: "In src/onward/artifacts.py, update report_rows() and select_next_artifact() to accept an optional claimed_ids: set[str] parameter (default empty set). When provided, tasks whose ID is in claimed_ids should be excluded from actionable results — report_rows should tag them separately so the caller can render a [Claimed] section, and select_next_artifact should skip them entirely."
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: []
files:
- "src/onward/artifacts.py"
acceptance:
- "report_rows accepts optional claimed_ids parameter"
- "Tasks in claimed_ids are excluded from the main actionable rows"
- "select_next_artifact accepts optional claimed_ids parameter"
- "select_next_artifact never returns a task whose ID is in claimed_ids"
created_at: "2026-03-21T02:11:28Z"
updated_at: "2026-03-21T03:17:32Z"
effort: "m"
---

# Context

In src/onward/artifacts.py, update report_rows() and select_next_artifact() to accept an optional claimed_ids: set[str] parameter (default empty set). When provided, tasks whose ID is in claimed_ids should be excluded from actionable results — report_rows should tag them separately so the caller can render a [Claimed] section, and select_next_artifact should skip them entirely.

# Scope

- In src/onward/artifacts.py, update report_rows() and select_next_artifact() to accept an optional claimed_ids: set[str] parameter (default empty set). When provided, tasks whose ID is in claimed_ids should be excluded from actionable results — report_rows should tag them separately so the caller can render a [Claimed] section, and select_next_artifact should skip them entirely.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/artifacts.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- report_rows accepts optional claimed_ids parameter
- Tasks in claimed_ids are excluded from the main actionable rows
- select_next_artifact accepts optional claimed_ids parameter
- select_next_artifact never returns a task whose ID is in claimed_ids

# Handoff notes
