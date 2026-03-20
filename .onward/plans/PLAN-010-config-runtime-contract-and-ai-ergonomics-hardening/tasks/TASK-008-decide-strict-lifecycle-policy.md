---
id: "TASK-008"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-004"
project: ""
title: "Decide strict lifecycle policy"
status: "completed"
description: "Choose and document whether work owns transitions or users do"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:22Z"
updated_at: "2026-03-20T00:50:44Z"
---

# Context

PLAN-010 phase 2 step 4: pick **one** lifecycle model so docs and mental models match reality. Plan options: strict manual (`start` → work → `complete`) vs **work-owned** transitions.

# Scope

- Record the **authoritative policy** (work-owned execution + manual `start`/`complete`/`cancel` overlays) in a canonical doc.
- Align high-traffic agent docs (`AGENTS.md`, README loop, INSTALLATION paste blocks) with that policy so they are not stricter than the CLI.

# Out of scope

- Rewriting every peripheral doc (TASK-010); changing validation in code (TASK-009).

# Files to inspect

- `docs/LIFECYCLE.md` (new), `AGENTS.md`, `README.md`, `INSTALLATION.md`, `docs/CONTRIBUTION.md`, `docs/WORK_HANDOFF.md`, `src/onward/execution.py` (`_work_task`), `src/onward/artifacts.py` (`_transition_status`)

# Implementation notes

- Policy must match `_work_task` (auto-`completed` on success, `open` on failure) unless TASK-009 deliberately changes code later.

# Acceptance criteria

- `docs/LIFECYCLE.md` exists and states the decision; agent-facing instructions no longer imply mandatory `complete` after every successful `work`.

# Handoff notes

- **Policy:** *Work-owned execution, manual overlays* — `onward work` drives status around executor runs (task → `completed` on success, `open` on failure; chunk → `in_progress` then `completed` after post hook). `start` / `complete` / `cancel` are explicit, non-executor transitions; `start` is optional before `work`.
- **Canonical doc:** `docs/LIFECYCLE.md` (references TASK-009 for CLI alignment/tests, TASK-010 for any remaining doc sweep).
- **Aligned now:** `AGENTS.md`, `README.md` (loop + momentum), `INSTALLATION.md` (all agent paste blocks + first-run), `docs/CONTRIBUTION.md`, `docs/WORK_HANDOFF.md`.
- **Rejected alternative for this plan:** strict manual-only (`start` → external work → `complete` every time) — would contradict current `_work_task` behavior and duplicate status updates after successful `work`.
