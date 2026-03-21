---
id: "TASK-033"
type: "task"
plan: "PLAN-004"
chunk: "CHUNK-009"
project: ""
title: "Implement format_report_markdown function"
status: "completed"
description: "Create format_report_markdown function that returns clean markdown with headers, tables, checkboxes"
human: false
model: "claude-sonnet-4-5"
effort: "m"
depends_on:
- "TASK-032"
files:
- "src/onward/cli_commands.py"
acceptance:
- "Function returns valid GitHub-flavored markdown string"
- "All 8 report sections present (9 with verbose)"
- "No ANSI escape codes in output"
- "Empty sections show '*None*' italic"
- "Tables have proper header and separator rows"
- "Active work tree renders as fenced code block"
created_at: "2026-03-21T15:50:09Z"
updated_at: "2026-03-21T16:17:25Z"
run_count: 1
last_run_status: "completed"
---

# Context

<!-- What this task is doing and where it fits in the chunk. -->

# Scope

<!-- Tight, concrete bullets. Keep this task small and finishable. -->

# Out of scope

<!-- Explicitly exclude adjacent work. -->

# Files to inspect

<!-- Start here. Include exact paths when known. -->

# Implementation notes

<!-- Constraints, gotchas, and edge cases to handle. -->

# Acceptance criteria

<!-- Binary checks: tests, outputs, behavior changes, docs updates. -->

# Handoff notes

The `format_report_markdown()` function has been fully implemented in `cli_commands.py` (lines 1363-1578) and integrated into `cmd_report()` (lines 1594-1606).

**Verified functionality:**
- ✅ All 8 report sections present (9 with `--verbose`)
- ✅ No ANSI escape codes in output (verified with grep)
- ✅ Empty sections display as `*None*` (italic)
- ✅ Tables have proper header and separator rows (`|---|`)
- ✅ Active work tree renders as fenced code block
- ✅ Works with `--verbose` flag (shows Run Stats table)
- ✅ Works with `--project` flag (filters correctly)
- ✅ Already wired into `cmd_report` with early return on `args.md`

**Next task (TASK-034):**
The function is already wired into `cmd_report`, so TASK-034 should focus on adding comprehensive tests to verify all edge cases and markdown structure.
