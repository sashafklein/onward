---
id: "TASK-032"
type: "task"
plan: "PLAN-004"
chunk: "CHUNK-009"
project: ""
title: "Add --md argument to report subparser in cli.py"
status: "in_progress"
description: "Add --md boolean flag to the report subparser argument definitions"
human: false
model: "claude-sonnet-4-5"
effort: "xs"
depends_on: []
files:
- "src/onward/cli.py"
acceptance:
- "--md argument exists on report subparser"
- "Default is False"
- "onward report --help shows --md option"
created_at: "2026-03-21T15:50:08Z"
updated_at: "2026-03-21T16:10:58Z"
run_count: 1
last_run_status: "failed"
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
