---
id: "CHUNK-011"
type: "chunk"
plan: "PLAN-011"
project: ""
title: "Structured feedback and recovery"
status: "completed"
description: "Executor returns structured results (files changed, follow-ups, acceptance status). Recovery docs for failure handling."
priority: "medium"
model: "sonnet-latest"
estimated_files: 18
depends_on:
  - "CHUNK-008"
  - "CHUNK-009"
created_at: "2026-03-20T15:52:26Z"
updated_at: "2026-03-20T18:23:00Z"
---

# Summary

Define and implement a structured result schema for executor output. When a task completes, the executor can report files changed, follow-up work discovered, and acceptance criteria status. Onward parses this, auto-creates follow-up tasks, and stores results for display. Also add recovery documentation for when things go wrong.

# Scope

- Define `onward_task_result` v2 schema with: summary, files_changed, follow_ups, acceptance_met/unmet
- Onward parses structured results from executor stdout
- follow_ups auto-created as new tasks in the current chunk
- `onward show TASK-X` displays structured results, run history, dependency graph
- New `docs/RECOVERY.md` with failure modes, retry guidance, intervention patterns
- Reference RECOVERY.md from AGENTS.md

# Out of scope

- Real-time progress streaming (future)
- Partial completion / resumable tasks (future)

# Dependencies

- CHUNK-008 (working executor)
- CHUNK-009 (failed status exists for recovery docs to reference)

# Expected files/systems involved

- `src/onward/executor_ack.py` — extended result parsing
- `src/onward/execution.py` — follow-up task creation, result storage
- `src/onward/cli_commands.py` — enhanced show command
- `docs/schemas/onward-task-result-v2.schema.json` — new schema
- `docs/RECOVERY.md` — new recovery guide
- `AGENTS.md` — reference recovery docs

# Completion criteria

- [ ] Executor can emit structured JSON with files_changed and follow_ups
- [ ] follow_ups in result are auto-created as tasks in the current chunk
- [ ] `onward show TASK-X` shows run history, structured results, retry count
- [ ] `docs/RECOVERY.md` covers: read logs, retry, skip, intervene, common failures
- [ ] AGENTS.md references RECOVERY.md
