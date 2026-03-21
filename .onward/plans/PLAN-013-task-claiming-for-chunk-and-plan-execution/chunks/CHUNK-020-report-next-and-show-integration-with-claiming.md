---
id: "CHUNK-020"
type: "chunk"
plan: "PLAN-013"
project: ""
title: "Report, next, and show integration with claiming"
status: "completed"
description: "Update cmd_report, cmd_next, and cmd_show to consume claimed_task_ids(). Report should show claimed tasks in a separate dimmed [Claimed] section rather than in actionable sections. Next should skip claimed tasks entirely. Show should display claimed-by-RUN info when a task is claimed. Pass claimed_ids through report_rows and select_next_artifact."
priority: "high"
model: "sonnet-latest"
depends_on:
- "CHUNK-019"
created_at: "2026-03-21T01:59:37Z"
updated_at: "2026-03-21T03:17:33Z"
---

# Summary

Update cmd_report, cmd_next, and cmd_show to consume claimed_task_ids(). Report should show claimed tasks in a separate dimmed [Claimed] section rather than in actionable sections. Next should skip claimed tasks entirely. Show should display claimed-by-RUN info when a task is claimed. Pass claimed_ids through report_rows and select_next_artifact.

# Scope

- Update cmd_report, cmd_next, and cmd_show to consume claimed_task_ids(). Report should show claimed tasks in a separate dimmed [Claimed] section rather than in actionable sections. Next should skip claimed tasks entirely. Show should display claimed-by-RUN info when a task is claimed. Pass claimed_ids through report_rows and select_next_artifact.

# Out of scope

- None specified.

# Dependencies

- CHUNK-019

# Expected files/systems involved

**Must touch:**
- `src/onward/cli_commands.py`
- `src/onward/artifacts.py`

# Completion criteria

- onward report shows claimed tasks in a [Claimed] section, not in [Upcoming] or [In Progress]
- onward next does not select a task whose parent chunk/plan is claimed
- onward show TASK-* displays claimed by RUN-... when the task is claimed
- report_rows and select_next_artifact accept optional claimed_ids parameter

# Notes
