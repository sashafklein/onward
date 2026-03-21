---
id: "TASK-064"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-017"
project: ""
title: "Update tests to match new task frontmatter (no files/acceptance keys, plus doctor warnings)"
status: "open"
description: "Several tests assert on task frontmatter content that will change after tasks 0 and 1 of this chunk.\n\n**`tests/test_cli_split.py` — `test_split_chunk_creates_task_with_acceptance`** (around line 49–71): The test currently asserts that `'acceptance:\\n  - \"returns 200\"'` (or similar) appears in the raw task file. After task 0, `acceptance` is no longer in the frontmatter; it still appears in the body's `# Acceptance criteria` section. Update the assertion to check for `'- returns 200'` (or `'returns 200'`) inside the body section instead of as a YAML frontmatter key. Make sure the assertion still validates that acceptance data made it to the file.\n\n**`tests/test_cli_artifacts.py` — `test_new_artifacts`** (around line 60–65): Remove or update the line `assert 'acceptance: []' in show_out` — after task 0 this field will no longer appear in the frontmatter displayed by `onward show`.\n\n**Add a new test in `tests/test_cli_artifacts.py`** (or `tests/test_cli_split.py`) that verifies the doctor warning for leftover fields: manually write a task file with `files: []` and `acceptance: []` in its frontmatter, then call `onward doctor` and assert the output contains `unknown task field 'files'` and `unknown task field 'acceptance'`. Use `_init_workspace` + `cli.main([\"new\", ...])` to create a real task, then open the file and patch in the extra frontmatter keys before running doctor."
human: false
model: "sonnet"
executor: "onward-exec"
depends_on:
- "TASK-062"
- "TASK-063"
files:
- "tests/test_cli_split.py"
- "tests/test_cli_artifacts.py"
acceptance:
- "All existing tests pass"
- "The acceptance-in-body assertion in `test_split_chunk_creates_task_with_acceptance` correctly verifies that acceptance text appears in the task file (body section)"
- "The stale `'acceptance: []' in show_out` assertion is removed from `test_new_artifacts`"
- "A new test confirms that `onward doctor` warns about `files` and `acceptance` as unknown task fields when they appear in frontmatter"
created_at: "2026-03-21T20:25:46Z"
updated_at: "2026-03-21T20:25:46Z"
effort: "m"
---

# Context

Several tests assert on task frontmatter content that will change after tasks 0 and 1 of this chunk.

**`tests/test_cli_split.py` — `test_split_chunk_creates_task_with_acceptance`** (around line 49–71): The test currently asserts that `'acceptance:\n  - "returns 200"'` (or similar) appears in the raw task file. After task 0, `acceptance` is no longer in the frontmatter; it still appears in the body's `# Acceptance criteria` section. Update the assertion to check for `'- returns 200'` (or `'returns 200'`) inside the body section instead of as a YAML frontmatter key. Make sure the assertion still validates that acceptance data made it to the file.

**`tests/test_cli_artifacts.py` — `test_new_artifacts`** (around line 60–65): Remove or update the line `assert 'acceptance: []' in show_out` — after task 0 this field will no longer appear in the frontmatter displayed by `onward show`.

**Add a new test in `tests/test_cli_artifacts.py`** (or `tests/test_cli_split.py`) that verifies the doctor warning for leftover fields: manually write a task file with `files: []` and `acceptance: []` in its frontmatter, then call `onward doctor` and assert the output contains `unknown task field 'files'` and `unknown task field 'acceptance'`. Use `_init_workspace` + `cli.main(["new", ...])` to create a real task, then open the file and patch in the extra frontmatter keys before running doctor.

# Scope

- Several tests assert on task frontmatter content that will change after tasks 0 and 1 of this chunk.

**`tests/test_cli_split.py` — `test_split_chunk_creates_task_with_acceptance`** (around line 49–71): The test currently asserts that `'acceptance:\n  - "returns 200"'` (or similar) appears in the raw task file. After task 0, `acceptance` is no longer in the frontmatter; it still appears in the body's `# Acceptance criteria` section. Update the assertion to check for `'- returns 200'` (or `'returns 200'`) inside the body section instead of as a YAML frontmatter key. Make sure the assertion still validates that acceptance data made it to the file.

**`tests/test_cli_artifacts.py` — `test_new_artifacts`** (around line 60–65): Remove or update the line `assert 'acceptance: []' in show_out` — after task 0 this field will no longer appear in the frontmatter displayed by `onward show`.

**Add a new test in `tests/test_cli_artifacts.py`** (or `tests/test_cli_split.py`) that verifies the doctor warning for leftover fields: manually write a task file with `files: []` and `acceptance: []` in its frontmatter, then call `onward doctor` and assert the output contains `unknown task field 'files'` and `unknown task field 'acceptance'`. Use `_init_workspace` + `cli.main(["new", ...])` to create a real task, then open the file and patch in the extra frontmatter keys before running doctor.

# Out of scope

- None specified.

# Files to inspect

- `tests/test_cli_split.py`
- `tests/test_cli_artifacts.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- All existing tests pass
- The acceptance-in-body assertion in `test_split_chunk_creates_task_with_acceptance` correctly verifies that acceptance text appears in the task file (body section)
- The stale `'acceptance: []' in show_out` assertion is removed from `test_new_artifacts`
- A new test confirms that `onward doctor` warns about `files` and `acceptance` as unknown task fields when they appear in frontmatter

# Handoff notes
