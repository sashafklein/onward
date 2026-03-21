---
id: "TASK-072"
type: "task"
plan: "PLAN-013"
chunk: "CHUNK-020"
project: ""
title: "Update cmd_report, cmd_next, and cmd_show for claiming"
status: "completed"
description: "In src/onward/cli_commands.py, update cmd_report to call claimed_task_ids(root) from execution.py and pass the result to report rendering. Claimed tasks should appear in a separate dimmed [Claimed] section, not in [Upcoming] or [In Progress]. Update cmd_next to call claimed_task_ids(root) and pass the set to select_next_artifact so claimed tasks are skipped. Update cmd_show to check if the displayed task is in the claimed set and if so, display \"Claimed by RUN-...\" with the parent run info from ongoing.json."
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on:
- "TASK-071"
files:
- "src/onward/cli_commands.py"
acceptance:
- "onward report shows claimed tasks in a [Claimed] section, not in [Upcoming] or [In Progress]"
- "onward next does not select a task whose parent chunk/plan is claimed"
- "onward show TASK-* displays \"Claimed by RUN-...\" when the task is claimed"
- "Report and next work correctly when no claims exist (empty claimed_ids)"
created_at: "2026-03-21T02:11:28Z"
updated_at: "2026-03-21T03:17:33Z"
effort: "m"
---

# Context

In src/onward/cli_commands.py, update cmd_report to call claimed_task_ids(root) from execution.py and pass the result to report rendering. Claimed tasks should appear in a separate dimmed [Claimed] section, not in [Upcoming] or [In Progress]. Update cmd_next to call claimed_task_ids(root) and pass the set to select_next_artifact so claimed tasks are skipped. Update cmd_show to check if the displayed task is in the claimed set and if so, display "Claimed by RUN-..." with the parent run info from ongoing.json.

# Scope

- In src/onward/cli_commands.py, update cmd_report to call claimed_task_ids(root) from execution.py and pass the result to report rendering. Claimed tasks should appear in a separate dimmed [Claimed] section, not in [Upcoming] or [In Progress]. Update cmd_next to call claimed_task_ids(root) and pass the set to select_next_artifact so claimed tasks are skipped. Update cmd_show to check if the displayed task is in the claimed set and if so, display "Claimed by RUN-..." with the parent run info from ongoing.json.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/cli_commands.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- onward report shows claimed tasks in a [Claimed] section, not in [Upcoming] or [In Progress]
- onward next does not select a task whose parent chunk/plan is claimed
- onward show TASK-* displays "Claimed by RUN-..." when the task is claimed
- Report and next work correctly when no claims exist (empty claimed_ids)

# Handoff notes
