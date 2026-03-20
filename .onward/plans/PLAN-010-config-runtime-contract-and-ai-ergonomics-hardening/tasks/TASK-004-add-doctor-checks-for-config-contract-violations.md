---
id: "TASK-004"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-002"
project: ""
title: "Add doctor checks for config-contract violations"
status: "completed"
description: "Fail fast when config contains unsupported, ignored, or contradictory settings"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:21Z"
updated_at: "2026-03-20T00:39:34Z"
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

- `validate_config_contract_issues()` in `src/onward/config.py` is the allowlist for `.onward.config.yaml`; extend `CONFIG_TOP_LEVEL_KEYS` / `CONFIG_SECTION_KEYS` when adding real config.
- Doctor reports removed keys (`path`, `work.create_worktree`, …), unknown keys, wrong types for `ralph.args` / shell hook lists, and ignored `sync.repo` when mode is `local` or `branch`.
- **Follow-up:** contract tests that diff scaffold template keys against `CONFIG_*` (TASK-013 / PLAN-010) would catch future drift.
