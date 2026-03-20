---
id: "TASK-028"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-002"
project: ""
title: "Re-evaluate local sync exit semantics"
status: "completed"
description: "Decide and document whether local-mode sync subcommands are no-op success or soft failure"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:53Z"
updated_at: "2026-03-20T14:53:50Z"
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

- **Policy (unchanged, now explicit):** `sync status` in **local** mode → exit **0** (informational). `sync push` / `pull` in **local** mode → exit **1** with stable messages so CI/scripts do not treat a mirror as having run.
- Docs: README sync table, INSTALLATION “Local sync mode (default): exit codes”, `docs/AI_OPERATOR.md` sync + anti-pattern §7.
- `validate_sync_config`: warn when `sync.mode: local` with non-empty `sync.repo` (doctor); test `test_doctor_warns_sync_repo_in_local_mode`; `test_sync_pull_local_mode_errors` for pull exit 1.
