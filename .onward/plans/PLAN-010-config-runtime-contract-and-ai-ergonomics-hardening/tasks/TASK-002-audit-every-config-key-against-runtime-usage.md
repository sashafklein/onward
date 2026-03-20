---
id: "TASK-002"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-002"
project: ""
title: "Audit every config key against runtime usage"
status: "completed"
description: "Build a key-by-key matrix of declared config, actual behavior, and drift"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:21Z"
updated_at: "2026-03-20T00:29:23Z"
has_notes: true
---

# Context

PLAN-010 phase 1: build an explicit **declared vs actual** inventory for configuration. The plan notes observed drift: template/docs keys not fully wired (`path`, `work.*`, `ralph.enabled`, etc.). This task establishes the evidence base for TASK-003 and doctor work.

# Scope

- Enumerate every key surfaced in `.onward.config.yaml` template / scaffold defaults and in README, INSTALLATION, CONTRIBUTION.
- For each key, trace runtime usage (read sites, defaults, ignored branches).
- Produce a single matrix (or checklist artifact): declared → implemented / partial / dead / contradictory.

# Out of scope

- Implementing fixes or removing keys (TASK-003).
- Non-config contract surfaces (executor payload, run files — other chunks).

# Files to inspect

- `src/onward/config.py`, `src/onward/scaffold.py`, `src/onward/cli.py`, `src/onward/execution.py`, `src/onward/sync.py`, `src/onward/split.py`
- `.onward/templates/` if present, `README.md`, `INSTALLATION.md`, `docs/CONTRIBUTION.md`

# Implementation notes

- Prefer grep/code search + short table in task notes or linked doc; keep repo truth in `.onward/plans/` if you add a scratch matrix file.
- Call out keys that are parsed but never affect behavior.

# Acceptance criteria

- Written matrix (or equivalent) covers all template + doc-mentioned config keys.
- Each key has a clear classification usable by TASK-003.

# Handoff notes

- Completed; matrix informed TASK-003/004 (see those tasks’ handoffs for resolved key set).
