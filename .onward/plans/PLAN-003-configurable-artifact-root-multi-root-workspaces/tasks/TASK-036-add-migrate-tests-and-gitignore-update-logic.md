---
id: "TASK-036"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-010"
project: ""
title: "Add migrate tests and gitignore update logic"
status: "open"
description: "Tests for migrate command and logic to update .gitignore entries from old to new root"
human: false
model: "claude-sonnet-4-5"
effort: "s"
depends_on:
  - "TASK-035"
files:
  - "src/onward/cli_commands.py"
  - "src/onward/scaffold.py"
  - "tests/test_migrate.py"
acceptance:
  - "Test covers .onward/ → nb/ migration end-to-end"
  - "Test covers --dry-run mode"
  - "Test covers --force overwrite"
  - ".gitignore entries updated from old root paths to new root paths"
  - "onward doctor passes after migration"
created_at: "2026-03-21T16:05:06Z"
updated_at: "2026-03-21T16:05:06Z"
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
