---
id: "CHUNK-012"
type: "chunk"
plan: "PLAN-011"
project: ""
title: "Scale and ergonomics"
status: "open"
description: "Batch task creation, onward ready, effort metadata, multi-project filtering, index-based fast reads."
priority: "medium"
model: "sonnet-latest"
estimated_files: 20
depends_on:
  - "CHUNK-008"
created_at: "2026-03-20T15:52:26Z"
updated_at: "2026-03-20T15:52:26Z"
---

# Summary

Add the operations needed to work at scale: batch task creation for rapid enqueuing, `onward ready` for a cross-plan view of actionable work, effort/size metadata for scheduling, consistent multi-project filtering, and index-based reads for performance.

# Scope

- `onward new task CHUNK-X --batch tasks.json` for bulk creation
- `onward ready` command: all open plans → first ready chunk → first ready task, grouped by project
- `effort` field on tasks/chunks (xs/s/m/l/xl), `estimated_files` on chunks
- `--project` filtering on all read commands, project inheritance (plan → chunk → task)
- `onward list` / `onward next` / `onward ready` use index.yaml when available
- Staleness detection via index_version counter

# Out of scope

- Cross-workspace dependencies
- Project-level configuration files
- Web dashboard

# Dependencies

- CHUNK-008 (basic executor infrastructure)

# Expected files/systems involved

- `src/onward/cli.py` — ready subcommand, batch flag
- `src/onward/cli_commands.py` — ready handler, batch handler
- `src/onward/artifacts.py` — index-based reads, project inheritance
- tests for ready, batch, project filtering

# Completion criteria

- [ ] `onward new task CHUNK-X --batch tasks.json` creates N tasks from JSON array
- [ ] `onward ready` shows actionable work across all plans, grouped by project
- [ ] `effort` metadata is accepted and displayed in report/tree
- [ ] `--project` works on list, next, ready, report, tree
- [ ] index.yaml is read by list/next/ready for fast path
