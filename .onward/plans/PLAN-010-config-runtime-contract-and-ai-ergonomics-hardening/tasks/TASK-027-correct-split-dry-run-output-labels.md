---
id: "TASK-027"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-004"
project: ""
title: "Correct split dry-run output labels"
status: "completed"
description: "Ensure dry-run prefixes match artifact type being created"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:52Z"
updated_at: "2026-03-20T14:53:49Z"
---

# Context

PLAN-010 phase 2 **§5**: **`onward split --dry-run`** labels must match **artifact type** (plan→chunks vs chunk→tasks) — avoid misleading “would create X” wording.

# Scope

- Fix dry-run printer in `split` command path: correct nouns per parent type.
- Add/adjust tests on captured output.

# Out of scope

- Changing split heuristics or AI prompts; model-backed vs fallback logic (document in TASK-010).

# Files to inspect

- `src/onward/split.py`, `src/onward/cli.py`, `tests/test_cli_split.py` (or equivalent)

# Implementation notes

- Golden strings in tests prevent regression.

# Acceptance criteria

- Tests assert correct labels for plan split vs chunk split dry-run.

# Handoff notes

- `cmd_split` dry-run: header `Split dry-run (plan→chunks|chunk→tasks)`, per-line `CHUNK: create` vs `TASK: create` (`cli_commands.py`).
- Tests: `test_split_plan_dry_run_*` golden strings; new `test_split_chunk_dry_run_labels_tasks`.
