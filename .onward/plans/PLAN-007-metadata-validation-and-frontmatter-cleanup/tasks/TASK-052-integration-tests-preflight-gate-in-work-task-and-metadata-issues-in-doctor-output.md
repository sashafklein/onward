---
id: "TASK-052"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-015"
project: ""
title: "Integration tests: preflight gate in work_task and metadata issues in doctor output"
status: "in_progress"
description: "Add integration tests to two existing test files.\n\n**In `tests/test_cli_work.py`**, add two tests that use the existing `_init_workspace` + CLI pattern:\n1. `test_work_task_preflight_rejects_bad_complexity`: create a workspace, add a plan/chunk/task, then directly edit the task file to add `complexity: banana` in the frontmatter. Run `cli.main(['work', 'TASK-001', '--root', str(tmp_path)])`. Assert exit code is non-zero and the task's status is still `open` (read it back via `must_find_by_id` or parse the file).\n2. `test_work_task_preflight_rejects_bad_model`: same setup but inject `model: nonexistent-model-xyz`. Assert exit code non-zero and status remains `open`.\n\n**In `tests/test_cli_init_doctor.py`**, add one test:\n3. `test_doctor_reports_metadata_issues`: init workspace, create a plan/chunk/task via CLI, directly edit the task file to inject `complexity: banana`. Run `cli.main(['doctor', '--root', str(tmp_path)])`. Assert exit code non-zero and the captured output contains the task's file path or ID along with the invalid value.\n\nFor editing artifact files in tests, use standard `Path.read_text` / `Path.write_text` to replace the frontmatter field."
human: false
model: "sonnet"
executor: "onward-exec"
depends_on:
- "TASK-049"
- "TASK-050"
files:
- "tests/test_cli_work.py"
- "tests/test_cli_init_doctor.py"
acceptance:
- "test_work_task_preflight_rejects_bad_complexity passes: exit code != 0 and task stays open"
- "test_work_task_preflight_rejects_bad_model passes: exit code != 0 and task stays open"
- "test_doctor_reports_metadata_issues passes: exit code != 0 and output references the bad field"
- "All previously existing tests in both files continue to pass"
created_at: "2026-03-21T20:20:59Z"
updated_at: "2026-03-21T20:49:37Z"
effort: "m"
run_count: 1
---

# Context

Add integration tests to two existing test files.

**In `tests/test_cli_work.py`**, add two tests that use the existing `_init_workspace` + CLI pattern:
1. `test_work_task_preflight_rejects_bad_complexity`: create a workspace, add a plan/chunk/task, then directly edit the task file to add `complexity: banana` in the frontmatter. Run `cli.main(['work', 'TASK-001', '--root', str(tmp_path)])`. Assert exit code is non-zero and the task's status is still `open` (read it back via `must_find_by_id` or parse the file).
2. `test_work_task_preflight_rejects_bad_model`: same setup but inject `model: nonexistent-model-xyz`. Assert exit code non-zero and status remains `open`.

**In `tests/test_cli_init_doctor.py`**, add one test:
3. `test_doctor_reports_metadata_issues`: init workspace, create a plan/chunk/task via CLI, directly edit the task file to inject `complexity: banana`. Run `cli.main(['doctor', '--root', str(tmp_path)])`. Assert exit code non-zero and the captured output contains the task's file path or ID along with the invalid value.

For editing artifact files in tests, use standard `Path.read_text` / `Path.write_text` to replace the frontmatter field.

# Scope

- Add integration tests to two existing test files.

**In `tests/test_cli_work.py`**, add two tests that use the existing `_init_workspace` + CLI pattern:
1. `test_work_task_preflight_rejects_bad_complexity`: create a workspace, add a plan/chunk/task, then directly edit the task file to add `complexity: banana` in the frontmatter. Run `cli.main(['work', 'TASK-001', '--root', str(tmp_path)])`. Assert exit code is non-zero and the task's status is still `open` (read it back via `must_find_by_id` or parse the file).
2. `test_work_task_preflight_rejects_bad_model`: same setup but inject `model: nonexistent-model-xyz`. Assert exit code non-zero and status remains `open`.

**In `tests/test_cli_init_doctor.py`**, add one test:
3. `test_doctor_reports_metadata_issues`: init workspace, create a plan/chunk/task via CLI, directly edit the task file to inject `complexity: banana`. Run `cli.main(['doctor', '--root', str(tmp_path)])`. Assert exit code non-zero and the captured output contains the task's file path or ID along with the invalid value.

For editing artifact files in tests, use standard `Path.read_text` / `Path.write_text` to replace the frontmatter field.

# Out of scope

- None specified.

# Files to inspect

- `tests/test_cli_work.py`
- `tests/test_cli_init_doctor.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- test_work_task_preflight_rejects_bad_complexity passes: exit code != 0 and task stays open
- test_work_task_preflight_rejects_bad_model passes: exit code != 0 and task stays open
- test_doctor_reports_metadata_issues passes: exit code != 0 and output references the bad field
- All previously existing tests in both files continue to pass

# Handoff notes
