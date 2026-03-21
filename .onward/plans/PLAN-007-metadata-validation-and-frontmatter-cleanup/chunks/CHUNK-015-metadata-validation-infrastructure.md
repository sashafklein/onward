---
id: "CHUNK-015"
type: "chunk"
plan: "PLAN-007"
project: ""
title: "Metadata validation infrastructure"
status: "completed"
description: "Define KNOWN_FIELDS per artifact type and FIELD_VALIDATORS in artifacts.py (status, priority, effort/complexity compat, model, human). Expand validate_artifact() to run field validators and warn on unknown fields. Add validate_task_preflight() in execution.py called before marking in_progress in _work_task(). Surface richer issues in cmd_doctor(). Add tests covering validation logic, pre-flight gate, and doctor output."
priority: "high"
model: "sonnet"
depends_on: []
created_at: "2026-03-21T20:18:55Z"
updated_at: "2026-03-21T20:51:31Z"
---

# Summary

Define KNOWN_FIELDS per artifact type and FIELD_VALIDATORS in artifacts.py (status, priority, effort/complexity compat, model, human). Expand validate_artifact() to run field validators and warn on unknown fields. Add validate_task_preflight() in execution.py called before marking in_progress in _work_task(). Surface richer issues in cmd_doctor(). Add tests covering validation logic, pre-flight gate, and doctor output.

# Scope

- Define KNOWN_FIELDS per artifact type and FIELD_VALIDATORS in artifacts.py (status, priority, effort/complexity compat, model, human). Expand validate_artifact() to run field validators and warn on unknown fields. Add validate_task_preflight() in execution.py called before marking in_progress in _work_task(). Surface richer issues in cmd_doctor(). Add tests covering validation logic, pre-flight gate, and doctor output.

# Out of scope

- None specified.

# Dependencies

- None specified.

# Expected files/systems involved

**Must touch:**
- `src/onward/artifacts.py`
- `src/onward/execution.py`
- `src/onward/cli_commands.py`

**Likely:**
- `tests/test_preflight.py`
- `tests/test_cli_init_doctor.py`
- `tests/test_cli_work.py`
- `tests/test_architecture_seams.py`

**Deferred / out of scope for this chunk:**
- `docs/`

# Completion criteria

- validate_artifact() returns errors for bad status, bad priority, bad complexity/effort value, and unknown frontmatter fields
- onward work TASK-X with complexity: banana exits with a clear error and leaves the task in open status
- onward work TASK-X with model: nonexistent-model exits with a clear error and leaves the task in open status
- onward doctor reports all metadata issues found across a workspace
- All existing tests pass

# Notes
