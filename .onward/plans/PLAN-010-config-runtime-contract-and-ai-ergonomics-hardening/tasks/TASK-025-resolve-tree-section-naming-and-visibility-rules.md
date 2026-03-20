---
id: "TASK-025"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-004"
project: ""
title: "Resolve tree section naming and visibility rules"
status: "open"
description: "Either filter completed leaves from open tree or rename section to match output"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:52Z"
updated_at: "2026-03-20T00:28:52Z"
---

# Context

PLAN-010 phase 2 **§5**: **`onward tree`** section naming vs filtering is ambiguous — users/agents misread which tasks appear under which headings.

# Scope

- Decide consistent naming for tree sections (open / in-progress / blocked / human-only, etc.).
- Align implementation in `cmd_tree` (or service) with those names; update help text.

# Out of scope

- `(A)`/`(H)` legend prose (TASK-026) — coordinate wording.

# Files to inspect

- `src/onward/cli.py` (`cmd_tree`), tests for tree output, `README.md`

# Implementation notes

- Prefer minimal rename if behavior is already correct; otherwise fix filtering logic.

# Acceptance criteria

- Golden output or snapshot tests updated; README/help match behavior.

# Handoff notes

<!-- Fill when closing. -->
