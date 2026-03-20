---
id: "TASK-029"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-008"
project: ""
title: "Rename ralph to executor throughout codebase"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files:
  - src/onward/config.py
  - src/onward/execution.py
  - src/onward/preflight.py
  - src/onward/cli_commands.py
  - src/onward/scaffold.py
  - tests/test_cli_work.py
  - tests/test_cli_review.py
  - tests/test_cli_split.py
  - tests/test_preflight.py
  - tests/test_architecture_seams.py
acceptance:
  - "grep -r 'ralph' src/onward/ returns zero hits outside backward-compat alias code"
  - "all existing tests pass after rename"
  - "onward doctor validates both executor: and ralph: config keys"
created_at: "2026-03-20T16:00:56Z"
updated_at: "2026-03-20T16:00:56Z"
---

# Context

This is the first task in CHUNK-008 (Executor foundation and dogfood enablement). The entire codebase currently uses "ralph" as the name for the external executor subprocess — config keys, function names, error messages, preflight checks, run records. Before any new executor work can proceed, this naming must be normalized to "executor" so the abstraction is tool-agnostic. Every subsequent task in this chunk builds on the renamed surface.

# Scope

- **config.py**: Rename `CONFIG_TOP_LEVEL_KEYS` entry from `"ralph"` to `"executor"`. Add backward-compat: if the loaded config contains a `ralph` key but no `executor` key, treat it as `executor` (log a deprecation warning on `onward doctor`). Rename `CONFIG_SECTION_KEYS["ralph"]` to `CONFIG_SECTION_KEYS["executor"]`. Rename `is_ralph_enabled` → `is_executor_enabled`. Update `validate_config_contract_issues` to check `executor` (accepting `ralph` with a deprecation notice). Rename `_workspace_ralph_argv` → `_workspace_executor_argv`. Update all internal `config.get("ralph", {})` calls to `config.get("executor", {})`.
- **execution.py**: Replace all `config.get("ralph", {})` with `config.get("executor", {})`. Update `import is_ralph_enabled` → `import is_executor_enabled`. Change `"executor": "ralph"` in run records to `"executor": command` (the actual command string). Update error messages: `"ralph.enabled is false"` → `"executor.enabled is false"`.
- **preflight.py**: Rename `preflight_ralph_command` → `preflight_executor_command`. Rename `_ralph_command` → `_executor_command`. Update internal `config.get("ralph", {})` → `config.get("executor", {})`. Update error message strings that mention `ralph.command` → `executor.command`.
- **cli_commands.py**: Update imports (`is_ralph_enabled` → `is_executor_enabled`, `preflight_ralph_command` → `preflight_executor_command`). Update `cmd_new_task` default metadata: `"executor": "ralph"` → `"executor": "onward-exec"`.
- **scaffold.py**: In `DEFAULT_FILES[".onward.config.yaml"]`, replace the `ralph:` section with `executor:` section. Change default command from `ralph` to `onward-exec`. Update comments accordingly.
- **hooks templates**: Update `executor: ralph` in `.onward/hooks/post-task.md` and `.onward/hooks/post-chunk.md` to `executor: onward-exec`.
- **All tests**: Update any references to `ralph` config keys, function names, and expected error messages.
- **Backward compat in config loading**: In `load_workspace_config` or a new helper, if `ralph` key exists and `executor` does not, copy `ralph` → `executor` in the returned dict. This lets existing `.onward.config.yaml` files keep working.

# Out of scope

- Creating the `scripts/onward-exec` script (TASK-030).
- Changing execution logic or adding plan-level work (TASK-031).
- Changing hook behavior (TASK-032).
- Documentation updates beyond inline error messages (TASK-033).
- Removing the `ralph` backward-compat alias (future task — keep it for at least one version).

# Files to inspect

- `src/onward/config.py` — primary: `CONFIG_TOP_LEVEL_KEYS`, `CONFIG_SECTION_KEYS`, `is_ralph_enabled`, `_workspace_ralph_argv`, `validate_config_contract_issues`, `_review_executor_from_entry`, `_legacy_plan_review_slots`, `build_plan_review_slots`
- `src/onward/execution.py` — `_execute_task_run` (lines ~180-188 ralph dict lookup), `work_task` (calls `preflight_ralph_command`), `run_chunk_post_markdown_hook` (lines ~424-431 ralph dict lookup), `execute_plan_review` (lines ~553-564 ralph dict lookup)
- `src/onward/preflight.py` — `_ralph_command`, `preflight_ralph_command`, `_first_invocation_token` (has `"ralph"` as default fallback)
- `src/onward/cli_commands.py` — `cmd_new_task` (`"executor": "ralph"` in metadata), imports from preflight and config
- `src/onward/scaffold.py` — `DEFAULT_FILES` (the `.onward.config.yaml` template, hook templates)
- `tests/test_cli_work.py`, `tests/test_cli_review.py`, `tests/test_cli_split.py`, `tests/test_preflight.py`, `tests/test_architecture_seams.py` — grep for `ralph` to find all references

# Implementation notes

- **Backward compat pattern**: Add a `_migrate_ralph_to_executor` helper in config.py that checks if `"ralph"` is in the config dict and `"executor"` is not. If so, move the value. This should be called in `load_workspace_config` before returning. On `onward doctor`, if `ralph` key is present, emit a warning like `"config key 'ralph' is deprecated; rename to 'executor'"`.
- **CONFIG_TOP_LEVEL_KEYS**: Add both `"executor"` and `"ralph"` to the frozenset during the transition period. The doctor validation should accept `ralph` with a deprecation warning rather than an error.
- **Default command change**: The default executor command changes from `"ralph"` to `"onward-exec"`. This appears in `_executor_command` (preflight.py) and `_workspace_executor_argv` (config.py) as the fallback when no command is configured. Also update `_first_invocation_token` default from `"ralph"` to `"onward-exec"`.
- **Run records**: The `"executor": "ralph"` literal in `_execute_task_run` should become the actual command string (e.g., `command` variable), not a hardcoded string.
- **Grep thoroughly**: Run `rg ralph src/ tests/` before and after to ensure no references are missed.
- **Test updates**: Many tests set up config dicts with `"ralph": {...}`. These should be updated to `"executor": {...}`. Tests that specifically test backward compat should use the `ralph` key intentionally.

# Acceptance criteria

- `rg -l ralph src/onward/` returns zero files (or only config.py with the backward-compat alias code)
- `pytest tests/` passes with no failures
- `onward doctor` on a workspace with `executor:` config reports no issues
- `onward doctor` on a workspace with legacy `ralph:` config reports a deprecation warning but no error
- Config with both `ralph:` and `executor:` keys: `executor` wins, doctor warns about `ralph` being ignored
- Error messages in execution.py and preflight.py say "executor" not "ralph"
- Run records written by `_execute_task_run` have `"executor": "<actual_command>"` not `"executor": "ralph"`

# Handoff notes

After this task, all source code uses "executor" terminology. The backward-compat alias ensures existing workspaces don't break. TASK-030 can now create `scripts/onward-exec` knowing the config refers to `executor.command: onward-exec`. TASK-031 and TASK-032 can build on the renamed APIs. TASK-033 will update docs to match.
