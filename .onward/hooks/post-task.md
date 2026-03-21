---
id: HOOK-post-task
type: hook
trigger: task.completed
model: opus
executor: onward-exec
scope: repo
---

# Purpose

Summarize what changed and propose next tasks.

# Inputs

- Completed task
- Run output

# Instructions

1. Confirm acceptance criteria status.
2. Note key files touched.
3. Propose follow-up tasks if needed.

# Required output

- Short completion summary
- Follow-up list (if any)
