---
id: "TASK-033"
type: "task"
plan: "PLAN-004"
chunk: "CHUNK-009"
project: ""
title: "Implement format_report_markdown function"
status: "open"
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
updated_at: "2026-03-21T15:50:09Z"
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

<!-- What the parent/next worker should know. Include follow-up ideas if discovered. -->
