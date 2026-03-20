---
id: "TASK-028"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-002"
project: ""
title: "Re-evaluate local sync exit semantics"
status: "open"
description: "Decide and document whether local-mode sync subcommands are no-op success or soft failure"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:53Z"
updated_at: "2026-03-20T00:28:53Z"
---

# Context

CHUNK-002 follow-up: when **`sync.mode: local`**, subcommands like **`onward sync push` / `pull` / `status`** currently reject with guidance — decide whether that should be **exit 0 no-op**, **non-zero soft failure**, or **consistent error** for scripting/CI, and document it.

# Scope

- Pick one semantics; align code, tests, and INSTALLATION/README troubleshooting.
- Ensure `doctor` and sync errors stay coherent (related to contradictory `sync.repo` in local mode).

# Out of scope

- Implementing new sync modes; remote sync behavior changes.

# Files to inspect

- `src/onward/sync.py`, `src/onward/cli.py`, `tests/test_sync.py`, `INSTALLATION.md`, `README.md`

# Implementation notes

- Prefer least surprise for automation: explicit non-zero with stable message vs silent success — choose and justify in task handoff.

# Acceptance criteria

- Documented policy + tests for exit code; no contradictory docs across INSTALLATION/README.

# Handoff notes

<!-- Fill when closing. -->
