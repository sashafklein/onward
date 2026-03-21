---
id: "TASK-060"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-016"
project: ""
title: "Tests: update all affected tests for the effort→complexity rename"
status: "open"
description: "Update the following test files to match the renamed API and changed values:\n\n**tests/test_cli_scale.py:**\n- Line 16: Change `from onward.util import normalize_effort` → `from onward.util import normalize_complexity`\n- `test_normalize_effort_case_insensitive` (~line 34): Rename to `test_normalize_complexity_case_insensitive`. Change assertions: `normalize_complexity('M')` is invalid (not a complexity value) so returns `''`; add `normalize_complexity('medium') == 'medium'`, `normalize_complexity('MEDIUM') == 'medium'`, `normalize_complexity('invalid') == ''`\n- `test_new_task_effort_stored` (~line 153): Rename to `test_new_task_complexity_stored`. Change `--effort` → `--complexity`, change value from `m` to `medium`. Change `art.metadata.get('effort') == 'm'` → `art.metadata.get('complexity') == 'medium'`\n\n**tests/test_cli_report_md.py (~lines 17-18):**\n- Change both `--effort m` → `--complexity medium` and `--effort s` → `--complexity low`\n\n**tests/test_architecture_seams.py:**\n- `test_resolve_model_for_task_effort_tiers` (~line 222): Rename to `test_resolve_model_for_task_complexity_tiers`. Change test dict keys from `'effort'` to `'complexity'`. Keep assertions unchanged.\n- `test_resolve_model_for_task_unknown_effort_falls_back_to_default_tier` (~line 242): Rename to include 'complexity'. Change `{'effort': 'xl'}` → `{'complexity': 'xl'}`, `{'effort': ''}` → `{'complexity': ''}`.\n- ~line 219: Change `{'model': 'custom-model', 'effort': 'low'}` → `{'model': 'custom-model', 'complexity': 'low'}`\n- ~line 252: Change `{'model': '', 'effort': 'low'}` → `{'model': '', 'complexity': 'low'}`\n- Add a new test `test_resolve_model_for_task_effort_compat_fallback` that verifies `resolve_model_for_task(cfg, {'effort': 'low'}) == 'L'` (the backward compat path still works).\n\n**tests/test_run_record_io.py (~lines 136-137):**\n- Change `effort: \"low\"` → `complexity: \"low\"` in the test fixture text substitution.\n\n**tests/test_cli_split.py:**\n- Read this file first; update any effort-key assertions or fixture data to use complexity."
human: false
model: "sonnet"
executor: "onward-exec"
depends_on:
- "TASK-053"
- "TASK-054"
- "TASK-055"
- "TASK-056"
- "TASK-057"
- "TASK-058"
- "TASK-059"
files:
- "tests/test_cli_scale.py"
- "tests/test_architecture_seams.py"
- "tests/test_cli_report_md.py"
- "tests/test_run_record_io.py"
- "tests/test_cli_split.py"
acceptance:
- "pytest tests/test_cli_scale.py passes with no failures"
- "pytest tests/test_architecture_seams.py passes with no failures"
- "pytest tests/test_cli_report_md.py passes with no failures"
- "pytest tests/test_run_record_io.py passes with no failures"
- "pytest tests/test_cli_split.py passes with no failures"
- "Zero grep matches for normalize_effort in test files"
- "New compat-fallback test in test_architecture_seams.py confirms effort key still resolves model"
created_at: "2026-03-21T20:23:52Z"
updated_at: "2026-03-21T20:23:52Z"
effort: "m"
---

# Context

Update the following test files to match the renamed API and changed values:

**tests/test_cli_scale.py:**
- Line 16: Change `from onward.util import normalize_effort` → `from onward.util import normalize_complexity`
- `test_normalize_effort_case_insensitive` (~line 34): Rename to `test_normalize_complexity_case_insensitive`. Change assertions: `normalize_complexity('M')` is invalid (not a complexity value) so returns `''`; add `normalize_complexity('medium') == 'medium'`, `normalize_complexity('MEDIUM') == 'medium'`, `normalize_complexity('invalid') == ''`
- `test_new_task_effort_stored` (~line 153): Rename to `test_new_task_complexity_stored`. Change `--effort` → `--complexity`, change value from `m` to `medium`. Change `art.metadata.get('effort') == 'm'` → `art.metadata.get('complexity') == 'medium'`

**tests/test_cli_report_md.py (~lines 17-18):**
- Change both `--effort m` → `--complexity medium` and `--effort s` → `--complexity low`

**tests/test_architecture_seams.py:**
- `test_resolve_model_for_task_effort_tiers` (~line 222): Rename to `test_resolve_model_for_task_complexity_tiers`. Change test dict keys from `'effort'` to `'complexity'`. Keep assertions unchanged.
- `test_resolve_model_for_task_unknown_effort_falls_back_to_default_tier` (~line 242): Rename to include 'complexity'. Change `{'effort': 'xl'}` → `{'complexity': 'xl'}`, `{'effort': ''}` → `{'complexity': ''}`.
- ~line 219: Change `{'model': 'custom-model', 'effort': 'low'}` → `{'model': 'custom-model', 'complexity': 'low'}`
- ~line 252: Change `{'model': '', 'effort': 'low'}` → `{'model': '', 'complexity': 'low'}`
- Add a new test `test_resolve_model_for_task_effort_compat_fallback` that verifies `resolve_model_for_task(cfg, {'effort': 'low'}) == 'L'` (the backward compat path still works).

**tests/test_run_record_io.py (~lines 136-137):**
- Change `effort: "low"` → `complexity: "low"` in the test fixture text substitution.

**tests/test_cli_split.py:**
- Read this file first; update any effort-key assertions or fixture data to use complexity.

# Scope

- Update the following test files to match the renamed API and changed values:

**tests/test_cli_scale.py:**
- Line 16: Change `from onward.util import normalize_effort` → `from onward.util import normalize_complexity`
- `test_normalize_effort_case_insensitive` (~line 34): Rename to `test_normalize_complexity_case_insensitive`. Change assertions: `normalize_complexity('M')` is invalid (not a complexity value) so returns `''`; add `normalize_complexity('medium') == 'medium'`, `normalize_complexity('MEDIUM') == 'medium'`, `normalize_complexity('invalid') == ''`
- `test_new_task_effort_stored` (~line 153): Rename to `test_new_task_complexity_stored`. Change `--effort` → `--complexity`, change value from `m` to `medium`. Change `art.metadata.get('effort') == 'm'` → `art.metadata.get('complexity') == 'medium'`

**tests/test_cli_report_md.py (~lines 17-18):**
- Change both `--effort m` → `--complexity medium` and `--effort s` → `--complexity low`

**tests/test_architecture_seams.py:**
- `test_resolve_model_for_task_effort_tiers` (~line 222): Rename to `test_resolve_model_for_task_complexity_tiers`. Change test dict keys from `'effort'` to `'complexity'`. Keep assertions unchanged.
- `test_resolve_model_for_task_unknown_effort_falls_back_to_default_tier` (~line 242): Rename to include 'complexity'. Change `{'effort': 'xl'}` → `{'complexity': 'xl'}`, `{'effort': ''}` → `{'complexity': ''}`.
- ~line 219: Change `{'model': 'custom-model', 'effort': 'low'}` → `{'model': 'custom-model', 'complexity': 'low'}`
- ~line 252: Change `{'model': '', 'effort': 'low'}` → `{'model': '', 'complexity': 'low'}`
- Add a new test `test_resolve_model_for_task_effort_compat_fallback` that verifies `resolve_model_for_task(cfg, {'effort': 'low'}) == 'L'` (the backward compat path still works).

**tests/test_run_record_io.py (~lines 136-137):**
- Change `effort: "low"` → `complexity: "low"` in the test fixture text substitution.

**tests/test_cli_split.py:**
- Read this file first; update any effort-key assertions or fixture data to use complexity.

# Out of scope

- None specified.

# Files to inspect

- `tests/test_cli_scale.py`
- `tests/test_architecture_seams.py`
- `tests/test_cli_report_md.py`
- `tests/test_run_record_io.py`
- `tests/test_cli_split.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- pytest tests/test_cli_scale.py passes with no failures
- pytest tests/test_architecture_seams.py passes with no failures
- pytest tests/test_cli_report_md.py passes with no failures
- pytest tests/test_run_record_io.py passes with no failures
- pytest tests/test_cli_split.py passes with no failures
- Zero grep matches for normalize_effort in test files
- New compat-fallback test in test_architecture_seams.py confirms effort key still resolves model

# Handoff notes
