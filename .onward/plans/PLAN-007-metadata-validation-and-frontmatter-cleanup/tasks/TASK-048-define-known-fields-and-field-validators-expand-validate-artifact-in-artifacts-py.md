---
id: "TASK-048"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-015"
project: ""
title: "Define KNOWN_FIELDS and FIELD_VALIDATORS; expand validate_artifact() in artifacts.py"
status: "completed"
description: "In `src/onward/artifacts.py`:\n\n1. Add a `KNOWN_FIELDS` dict alongside the existing `REQUIRED_FIELDS`. For each artifact type (`plan`, `chunk`, `task`) list all recognized optional fields (e.g. `priority`, `effort`, `complexity`, `model`, `human`, `depends_on`, `description`, `run_count`). This is used to detect unknown frontmatter keys.\n\n2. Add a `FIELD_VALIDATORS` dict mapping field name → `(value) -> str | None` callable. Implement validators for:\n   - `status`: must be one of `{open, in_progress, completed, canceled, failed}`\n   - `priority`: must be one of `{high, medium, low}`\n   - `effort` / `complexity`: must be one of `{xs, s, m, l, xl}` (both fields share the same allowed set; they are treated as equivalent aliases)\n   - `model`: must match a short alias from `MODEL_ALIASES` in `onward.config` OR start with `claude-` or `codex-` (allow pass-through for full model IDs); reject values that clearly don't match any known pattern\n   - `human`: must be a Python `bool` (or YAML `true`/`false`)\n\n3. Expand `validate_artifact()` to:\n   - For each field present in `artifact.metadata` that is in `FIELD_VALIDATORS`, run the validator and append any returned error string as `\"{path}: {error}\"`.\n   - After required-field and validator checks, warn on any field key not present in `REQUIRED_FIELDS[type] + KNOWN_FIELDS[type]` by appending `\"{path}: unknown field '{key}'\"` to issues.\n   - The existing status check already present should be absorbed into the FIELD_VALIDATORS approach (avoid duplicate status validation)."
human: false
model: "sonnet"
executor: "onward-exec"
depends_on: []
files:
- "src/onward/artifacts.py"
acceptance:
- "validate_artifact() returns an issue for a task artifact with `complexity: banana`"
- "validate_artifact() returns an issue for a task artifact with `model: nonexistent-model-xyz`"
- "validate_artifact() returns an issue for a task artifact with `priority: urgent` (not in allowed set)"
- "validate_artifact() returns an issue for a task artifact with `human: maybe` (not a bool)"
- "validate_artifact() returns an issue for a task artifact with an unrecognized frontmatter key like `foobar: 123`"
- "validate_artifact() returns no issues for a well-formed task artifact with valid optional fields"
- "Existing tests that call validate_artifact() continue to pass"
created_at: "2026-03-21T20:20:59Z"
updated_at: "2026-03-21T20:36:26Z"
effort: "m"
run_count: 1
last_run_status: "completed"
---

# Context

In `src/onward/artifacts.py`:

1. Add a `KNOWN_FIELDS` dict alongside the existing `REQUIRED_FIELDS`. For each artifact type (`plan`, `chunk`, `task`) list all recognized optional fields (e.g. `priority`, `effort`, `complexity`, `model`, `human`, `depends_on`, `description`, `run_count`). This is used to detect unknown frontmatter keys.

2. Add a `FIELD_VALIDATORS` dict mapping field name → `(value) -> str | None` callable. Implement validators for:
   - `status`: must be one of `{open, in_progress, completed, canceled, failed}`
   - `priority`: must be one of `{high, medium, low}`
   - `effort` / `complexity`: must be one of `{xs, s, m, l, xl}` (both fields share the same allowed set; they are treated as equivalent aliases)
   - `model`: must match a short alias from `MODEL_ALIASES` in `onward.config` OR start with `claude-` or `codex-` (allow pass-through for full model IDs); reject values that clearly don't match any known pattern
   - `human`: must be a Python `bool` (or YAML `true`/`false`)

3. Expand `validate_artifact()` to:
   - For each field present in `artifact.metadata` that is in `FIELD_VALIDATORS`, run the validator and append any returned error string as `"{path}: {error}"`.
   - After required-field and validator checks, warn on any field key not present in `REQUIRED_FIELDS[type] + KNOWN_FIELDS[type]` by appending `"{path}: unknown field '{key}'"` to issues.
   - The existing status check already present should be absorbed into the FIELD_VALIDATORS approach (avoid duplicate status validation).

# Scope

- In `src/onward/artifacts.py`:

1. Add a `KNOWN_FIELDS` dict alongside the existing `REQUIRED_FIELDS`. For each artifact type (`plan`, `chunk`, `task`) list all recognized optional fields (e.g. `priority`, `effort`, `complexity`, `model`, `human`, `depends_on`, `description`, `run_count`). This is used to detect unknown frontmatter keys.

2. Add a `FIELD_VALIDATORS` dict mapping field name → `(value) -> str | None` callable. Implement validators for:
   - `status`: must be one of `{open, in_progress, completed, canceled, failed}`
   - `priority`: must be one of `{high, medium, low}`
   - `effort` / `complexity`: must be one of `{xs, s, m, l, xl}` (both fields share the same allowed set; they are treated as equivalent aliases)
   - `model`: must match a short alias from `MODEL_ALIASES` in `onward.config` OR start with `claude-` or `codex-` (allow pass-through for full model IDs); reject values that clearly don't match any known pattern
   - `human`: must be a Python `bool` (or YAML `true`/`false`)

3. Expand `validate_artifact()` to:
   - For each field present in `artifact.metadata` that is in `FIELD_VALIDATORS`, run the validator and append any returned error string as `"{path}: {error}"`.
   - After required-field and validator checks, warn on any field key not present in `REQUIRED_FIELDS[type] + KNOWN_FIELDS[type]` by appending `"{path}: unknown field '{key}'"` to issues.
   - The existing status check already present should be absorbed into the FIELD_VALIDATORS approach (avoid duplicate status validation).

# Out of scope

- None specified.

# Files to inspect

- `src/onward/artifacts.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- validate_artifact() returns an issue for a task artifact with `complexity: banana`
- validate_artifact() returns an issue for a task artifact with `model: nonexistent-model-xyz`
- validate_artifact() returns an issue for a task artifact with `priority: urgent` (not in allowed set)
- validate_artifact() returns an issue for a task artifact with `human: maybe` (not a bool)
- validate_artifact() returns an issue for a task artifact with an unrecognized frontmatter key like `foobar: 123`
- validate_artifact() returns no issues for a well-formed task artifact with valid optional fields
- Existing tests that call validate_artifact() continue to pass

# Handoff notes
