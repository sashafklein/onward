---
id: "TASK-003"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-002"
project: ""
title: "Implement or remove dead config keys"
status: "completed"
description: "Either wire unused keys into runtime or delete them from templates/docs"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:21Z"
updated_at: "2026-03-20T00:32:52Z"
---

# Context

Follows TASK-002. PLAN-010 phase 1: **no zombie keys** — implement, remove, or deprecate every config key the template/docs expose.

# Scope

- Wire dead keys into runtime or delete from scaffold/templates/docs with migration notes where needed.
- Align dogfood and example configs.

# Out of scope

- Doctor allowlist mechanics (TASK-004); broad non-config refactors.

# Files to inspect

- `src/onward/config.py`, `src/onward/scaffold.py`, `cli.py`, `execution.py`, `sync.py`, `split.py`, README, INSTALLATION, `.dogfood/`

# Implementation notes

- Match documented intent; if docs were wrong, fix docs or defer to TASK-010.

# Acceptance criteria

- No remaining “declared but ignored” keys from the audit without deprecation path; tests for new behavior.

# Handoff notes

- **Removed** top-level `path` and unimplemented `work.create_worktree` / `work.worktree_root` / `work.base_branch` from scaffold, repo `.onward.config.yaml`, dogfood consumer config, INSTALLATION, and README (artifacts remain under `.onward/` only).
- **Wired** `ralph.enabled`: when false, pre/post **shell** hooks still run; executor-backed steps (markdown hooks, task subprocess, `review-plan`, `post_chunk_markdown`) are skipped or fail with a clear message.
- **Wired** `work.sequential_by_default`: when false, `onward work CHUNK` runs at most one ready task per invocation; chunk stays `in_progress` until repeated runs finish all tasks.
- **Next:** TASK-004 (`doctor` checks for unknown/ignored keys) can treat the above as the supported key set; no migration needed for removed keys beyond docs (they were never enforced).
