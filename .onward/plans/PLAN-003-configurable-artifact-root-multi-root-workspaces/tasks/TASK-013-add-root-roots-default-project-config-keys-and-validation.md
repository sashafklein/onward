---
id: "TASK-013"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-003"
project: ""
title: "Add root/roots/default_project config keys and validation"
status: "completed"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "s"
depends_on:
- "TASK-012"
files: []
acceptance: []
created_at: "2026-03-21T15:49:13Z"
updated_at: "2026-03-21T16:23:22Z"
run_count: 1
last_run_status: "completed"
---

# Context

Config validation must recognize and validate the new `root`, `roots`, and `default_project` keys introduced by PLAN-003. Without validation, users get silent misconfiguration or confusing errors when both `root` and `roots` are set.

# Scope

- Add `root`, `roots`, `default_project` to `CONFIG_TOP_LEVEL_KEYS` in `src/onward/config.py`.
- Update `validate_config_contract_issues` to enforce:
  - `root` and `roots` are mutually exclusive — setting both is an error.
  - `root` value must be a non-empty string.
  - `roots` value must be a non-empty mapping of string keys to non-empty string values.
  - `default_project` must reference a key that exists in `roots` — error if it doesn't match.
  - `default_project` without `roots` is a warning (ignored in single-root mode).
- Remove or update any existing rejection of a `path` config key if it conflicts with root/roots awareness.

# Out of scope

- WorkspaceLayout dataclass definition (TASK-012).
- Directory existence checks (TASK-017 handles that in cmd_doctor).
- Wiring validation into scaffold or init flow.

# Files to inspect

- `src/onward/config.py` — `CONFIG_TOP_LEVEL_KEYS`, `validate_config_contract_issues`

# Implementation notes

- Validation returns a list of issue strings (existing pattern). Append new checks to the same list.
- The `root` value is a relative path string (e.g. `nb`, `.onward`, `plans/main`). Do not resolve or check existence here — that's doctor's job.
- `roots` example: `{frontend: .fe-plans, backend: .be-plans}`. Keys are project identifiers, values are relative paths.
- Keep backward compatibility: configs without `root` or `roots` remain valid (default `.onward`).

# Acceptance criteria

- `root`, `roots`, `default_project` are accepted without "unknown config key" warnings.
- `onward doctor` with valid `root: nb` config passes validation.
- Config with both `root` and `roots` set produces a clear error message.
- Config with `default_project: foo` but `roots: {bar: .bar}` produces an error.
- Config with neither `root` nor `roots` continues to work as before.

# Handoff notes

- TASK-017 depends on this to add directory-existence checks in doctor.
- If any existing tests assert against the exact set of `CONFIG_TOP_LEVEL_KEYS`, they will need updating.
