---
id: "TASK-035"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-010"
project: ""
title: "Implement onward migrate command with dry-run support"
status: "open"
description: "New onward migrate subcommand: detect old root, move contents to new configured root, --dry-run, --force"
human: false
model: "claude-sonnet-4-5"
effort: "m"
depends_on:
  - "TASK-015"
files:
  - "src/onward/cli.py"
  - "src/onward/cli_commands.py"
  - "src/onward/scaffold.py"
acceptance:
  - "onward migrate --dry-run prints planned moves"
  - "onward migrate moves all subdirs from .onward/ to configured root"
  - "Errors if source and target are the same"
  - "Errors if target has existing content without --force"
  - "Idempotent: no-op if source doesn't exist"
created_at: "2026-03-21T16:05:04Z"
updated_at: "2026-03-21T16:05:04Z"
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
