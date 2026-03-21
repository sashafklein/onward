---
id: "TASK-052"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-013"
project: ""
title: "Clean up hook system"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:10Z"
updated_at: "2026-03-20T21:03:12Z"
---

# Context

The hook system has accumulated unnecessary complexity. `pre_task_markdown` is defined in config but unused by default (null). The hooks aren't documented clearly. This task cleans up: remove the unused `pre_task_markdown` hook, add `pre_chunk_shell` for symmetry, and document the remaining hooks clearly.

# Scope

- Remove `pre_task_markdown` from the hook system:
  - Remove from `CONFIG_SECTION_KEYS["hooks"]` in `config.py`
  - Remove from `_execute_task_run` in `execution.py` (the `pre_md` variable and `_run_markdown_hook` call)
  - Remove from scaffold `.onward.config.yaml` default in `scaffold.py`
  - Remove from `validate_config_contract_issues` if referenced
- Add `pre_chunk_shell` hook:
  - Add to `CONFIG_SECTION_KEYS["hooks"]` in `config.py`
  - Add to scaffold config default
  - Wire into chunk execution in `cmd_work` chunk loop in `cli_commands.py` (run before the first task in a chunk)
  - Pattern: same as `_run_shell_hooks` used for `pre_task_shell`
- Document the final 5 hooks in `docs/WORK_HANDOFF.md`:
  - `pre_task_shell` — shell commands before each task
  - `post_task_shell` — shell commands after each task
  - `post_task_markdown` — markdown hook after each task (executor-backed)
  - `pre_chunk_shell` — shell commands before chunk execution starts (new)
  - `post_chunk_markdown` — markdown hook after chunk completion (executor-backed)
- Update the scaffold config comments to clearly explain each hook
- Add tests for `pre_chunk_shell` hook execution

# Out of scope

- Adding `pre_chunk_markdown` (too expensive — would invoke executor before every chunk)
- Adding plan-level hooks
- Hook ordering/priority system
- Async hook execution

# Files to inspect

- `src/onward/config.py` — `CONFIG_SECTION_KEYS["hooks"]` (line ~26)
- `src/onward/execution.py` — `_execute_task_run` (lines ~262-278 for pre hooks), `_run_shell_hooks`, `_run_markdown_hook`
- `src/onward/cli_commands.py` — `cmd_work` chunk loop for `pre_chunk_shell` integration
- `src/onward/scaffold.py` — `DEFAULT_FILES[".onward.config.yaml"]` hook section
- `docs/WORK_HANDOFF.md` — hook documentation

# Implementation notes

- For `pre_task_markdown` removal: in `_execute_task_run`, the code reads `pre_md = _hook_markdown_path(config, "pre_task_markdown")` and calls `_run_markdown_hook`. Remove both the variable assignment and the conditional block.
- For `pre_chunk_shell`: this runs once when `onward work CHUNK-X` starts (before the task loop), not before each task. Add it in `cmd_work` after `update_artifact_status(root, chunk, "in_progress")` and before the `while True:` loop.
- Use the existing `_hook_commands` and `_run_shell_hooks` pattern from `execution.py`. Import `_hook_commands` and `_run_shell_hooks` into the chunk command context, or add a public wrapper.
- Actually, `_run_shell_hooks` is private to `execution.py`. Either make it public, move the `pre_chunk_shell` logic into `execution.py` (cleaner), or add a `run_pre_chunk_shell_hooks(root)` function in `execution.py`.
- The scaffold config comment for `pre_chunk_shell` should explain: "Shell commands run once before chunk task execution starts (empty list means disabled)."
- The hook docs in `WORK_HANDOFF.md` should include: when each hook fires, what context it has, how to configure it, and an example use case (e.g., `pre_task_shell: ["git stash"]`, `post_task_shell: ["git add -A && git commit -m 'onward: task done'"]`).

# Acceptance criteria

- `pre_task_markdown` is removed from config schema, execution, and scaffold
- `onward doctor` rejects `pre_task_markdown` as unsupported config key
- `pre_chunk_shell` is wired and executes before chunk task loop
- `pre_chunk_shell` failure stops chunk execution with clear error
- `docs/WORK_HANDOFF.md` documents all 5 hooks with examples
- Scaffold config includes `pre_chunk_shell: []` with clear comment
- Tests cover: `pre_chunk_shell` execution, `pre_task_markdown` rejection in doctor

# Handoff notes

- The `_run_shell_hooks` and `_run_markdown_hook` functions in `execution.py` are currently private. If `pre_chunk_shell` is added in `execution.py`, keep them private. If added in `cli_commands.py`, they need to be made public or wrapped.
- Recommendation: add `run_pre_chunk_shell(root, config)` as a public function in `execution.py` to keep hook execution centralized.
- Future hooks to consider: `pre_plan_shell` (before plan execution), `post_plan_markdown` (after plan completion). Park these in FUTURE_ROADMAP.md (TASK-053).
