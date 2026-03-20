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

<!-- What this task is doing and where it fits in the chunk. -->

# Scope

<!-- Tight, concrete bullets. Keep this task small and finishable. -->

# Out of scope

<!-- Explicitly exclude adjacent work. -->

# Files to inspect

<!-- Start here. Include exact paths when known. -->

# Implementation notes

<!-- Constraints, gotchas, and edge cases to handle. -->

# Acceptance criteria

<!-- Binary checks: tests, outputs, behavior changes, docs updates. -->

# Handoff notes

- **Removed** top-level `path` and unimplemented `work.create_worktree` / `work.worktree_root` / `work.base_branch` from scaffold, repo `.onward.config.yaml`, dogfood consumer config, INSTALLATION, and README (artifacts remain under `.onward/` only).
- **Wired** `ralph.enabled`: when false, pre/post **shell** hooks still run; executor-backed steps (markdown hooks, task subprocess, `review-plan`, `post_chunk_markdown`) are skipped or fail with a clear message.
- **Wired** `work.sequential_by_default`: when false, `onward work CHUNK` runs at most one ready task per invocation; chunk stays `in_progress` until repeated runs finish all tasks.
- **Next:** TASK-004 (`doctor` checks for unknown/ignored keys) can treat the above as the supported key set; no migration needed for removed keys beyond docs (they were never enforced).
