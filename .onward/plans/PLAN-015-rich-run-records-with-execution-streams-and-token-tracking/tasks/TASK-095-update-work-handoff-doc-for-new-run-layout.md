---
id: "TASK-095"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-028"
project: ""
title: "Update WORK_HANDOFF.md for new run layout and ack schema v3"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on:
- "TASK-084"
- "TASK-090"
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:56:27Z"
---

# Context

External executors and contributors need to know about the new directory layout and
the updated ack schema. `docs/WORK_HANDOFF.md` is the canonical reference.

# Scope

- Document new run directory layout (`runs/TASK-XXX/info-*.json`, `summary-*.log`, `output-*.log`)
- Show example `info-*.json` with `files_changed` and `token_usage` fields
- Document ack schema v3 optional `token_usage` field with example JSON
- Note backward compatibility: legacy `RUN-*.json`/`.log` files remain readable
- Add a `tail -f` example for live output monitoring

# Out of scope

- Changing any code

# Files to inspect

- `docs/WORK_HANDOFF.md` — existing content and structure

# Implementation notes

- Keep additions to existing sections where possible; add a new "Run Records" section if none exists
- Include the directory tree from the plan's Phase 1 section as-is (it's already well-formatted)

# Acceptance criteria

- [ ] `docs/WORK_HANDOFF.md` includes the new run directory layout
- [ ] Example `info-*.json` with `token_usage` and `files_changed` shown
- [ ] Ack schema v3 `token_usage` field documented
- [ ] `tail -f` invocation example included

# Handoff notes

This is a docs-only task. No code changes needed.
