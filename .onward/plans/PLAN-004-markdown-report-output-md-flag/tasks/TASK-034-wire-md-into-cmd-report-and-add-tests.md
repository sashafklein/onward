---
id: "TASK-034"
type: "task"
plan: "PLAN-004"
chunk: "CHUNK-009"
project: ""
title: "Wire --md into cmd_report and add tests"
status: "open"
description: "Branch cmd_report on args.md, call formatter, add tests for no-ANSI and valid markdown"
human: false
model: "claude-sonnet-4-5"
effort: "s"
depends_on:
  - "TASK-033"
files:
  - "src/onward/cli_commands.py"
  - "tests/test_cli_report_md.py"
acceptance:
  - "onward report --md produces markdown output"
  - "onward report (without --md) produces ANSI output unchanged"
  - "Test captures --md output and verifies no \\033[ sequences"
  - "Test verifies ## headers and |---| table separators"
  - "--md with --project filters correctly"
  - "--md with --verbose includes run stats"
  - "--md with --no-color does not error"
created_at: "2026-03-21T15:50:10Z"
updated_at: "2026-03-21T15:50:10Z"
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
