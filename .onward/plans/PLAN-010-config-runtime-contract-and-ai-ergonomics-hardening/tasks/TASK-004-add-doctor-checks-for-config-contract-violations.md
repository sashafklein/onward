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

PLAN-010 acceptance: **`onward doctor`** catches unsupported/ignored/contradictory config and exits non-zero so drift is visible in CI and locally.

# Scope

- Validate shape and known keys; flag removed legacy keys; detect ignored combinations (e.g. `sync.repo` in local mode).
- Clear, actionable messages.

# Out of scope

- Validating remote git credentials over the network in doctor.

# Files to inspect

- `src/onward/config.py`, `src/onward/cli.py` (`cmd_doctor`), `tests/`

# Implementation notes

- Centralize allowlists (`CONFIG_TOP_LEVEL_KEYS`, section keys) — TASK-013 may add parity tests vs scaffold.

# Acceptance criteria

- Tests prove doctor fails on bad fixtures; docs mention what doctor checks.

# Handoff notes

- `validate_config_contract_issues()` in `src/onward/config.py` is the allowlist for `.onward.config.yaml`; extend `CONFIG_TOP_LEVEL_KEYS` / `CONFIG_SECTION_KEYS` when adding real config.
- Doctor reports removed keys (`path`, `work.create_worktree`, …), unknown keys, wrong types for `ralph.args` / shell hook lists, and ignored `sync.repo` when mode is `local` or `branch`.
- **Follow-up:** contract tests that diff scaffold template keys against `CONFIG_*` (TASK-013 / PLAN-010) would catch future drift.
