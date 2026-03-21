---
id: "TASK-051"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-015"
project: ""
title: "Unit tests for validate_artifact() field validators and unknown-field detection"
status: "completed"
description: "Create `tests/test_artifact_validation.py` with unit tests that exercise `validate_artifact()` in `onward.artifacts` directly, without a real filesystem workspace.\n\nUse `Artifact(file_path=Path('fake/TASK-001.md'), body='', metadata={...})` to construct test artifacts inline.\n\nCover:\n- Valid fully-formed task, chunk, and plan artifacts → no issues\n- Task with `status: garbage` → issue mentions 'status'\n- Task with `priority: urgent` → issue mentions 'priority'\n- Task with `effort: huge` → issue mentions 'effort'\n- Task with `complexity: banana` → issue mentions 'complexity'\n- Task with `model: nonexistent-model-xyz` → issue mentions 'model'\n- Task with `human: maybe` (string, not bool) → issue mentions 'human'\n- Task with unrecognized frontmatter key `foobar: 1` → issue mentions 'unknown field'\n- Task with valid optional fields (`effort: m`, `model: sonnet`, `human: true`, `priority: high`) → no issues\n- Artifact with unknown `type` field → existing behavior (issue about unknown type)"
human: false
model: "sonnet"
executor: "onward-exec"
depends_on:
- "TASK-048"
files:
- "tests/test_artifact_validation.py"
acceptance:
- "All new tests pass"
- "No existing tests are broken"
- "Tests are pure unit tests with no subprocess or filesystem I/O beyond constructing Path objects"
created_at: "2026-03-21T20:20:59Z"
updated_at: "2026-03-21T20:49:36Z"
effort: "m"
run_count: 1
last_run_status: "completed"
---

# Context

Create `tests/test_artifact_validation.py` with unit tests that exercise `validate_artifact()` in `onward.artifacts` directly, without a real filesystem workspace.

Use `Artifact(file_path=Path('fake/TASK-001.md'), body='', metadata={...})` to construct test artifacts inline.

Cover:
- Valid fully-formed task, chunk, and plan artifacts → no issues
- Task with `status: garbage` → issue mentions 'status'
- Task with `priority: urgent` → issue mentions 'priority'
- Task with `effort: huge` → issue mentions 'effort'
- Task with `complexity: banana` → issue mentions 'complexity'
- Task with `model: nonexistent-model-xyz` → issue mentions 'model'
- Task with `human: maybe` (string, not bool) → issue mentions 'human'
- Task with unrecognized frontmatter key `foobar: 1` → issue mentions 'unknown field'
- Task with valid optional fields (`effort: m`, `model: sonnet`, `human: true`, `priority: high`) → no issues
- Artifact with unknown `type` field → existing behavior (issue about unknown type)

# Scope

- Create `tests/test_artifact_validation.py` with unit tests that exercise `validate_artifact()` in `onward.artifacts` directly, without a real filesystem workspace.

Use `Artifact(file_path=Path('fake/TASK-001.md'), body='', metadata={...})` to construct test artifacts inline.

Cover:
- Valid fully-formed task, chunk, and plan artifacts → no issues
- Task with `status: garbage` → issue mentions 'status'
- Task with `priority: urgent` → issue mentions 'priority'
- Task with `effort: huge` → issue mentions 'effort'
- Task with `complexity: banana` → issue mentions 'complexity'
- Task with `model: nonexistent-model-xyz` → issue mentions 'model'
- Task with `human: maybe` (string, not bool) → issue mentions 'human'
- Task with unrecognized frontmatter key `foobar: 1` → issue mentions 'unknown field'
- Task with valid optional fields (`effort: m`, `model: sonnet`, `human: true`, `priority: high`) → no issues
- Artifact with unknown `type` field → existing behavior (issue about unknown type)

# Out of scope

- None specified.

# Files to inspect

- `tests/test_artifact_validation.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- All new tests pass
- No existing tests are broken
- Tests are pure unit tests with no subprocess or filesystem I/O beyond constructing Path objects

# Handoff notes
