---
id: "TASK-032"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-008"
project: ""
title: "Add default commit-after-task hook"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on:
  - "TASK-029"
blocked_by: []
files:
  - src/onward/scaffold.py
  - src/onward/execution.py
  - tests/test_cli_work.py
acceptance:
  - "onward init creates config with post_task_shell containing a git commit command"
  - "ONWARD_TASK_ID and ONWARD_TASK_TITLE env vars are set during hook execution"
  - "the default hook uses --allow-empty to avoid failure on clean worktrees"
created_at: "2026-03-20T16:00:56Z"
updated_at: "2026-03-20T16:00:56Z"
---

# Context

After each task completes successfully, Onward runs `post_task_shell` hooks. Currently the default config sets `post_task_shell: []` (empty — no hooks). This task adds a default commit hook so that each task completion produces a git commit with the task ID and title in the commit message. This creates a clean git history aligned with Onward's task structure and is essential for dogfooding: without it, task work accumulates uncommitted changes.

# Scope

- **scaffold.py**: Update the `DEFAULT_FILES[".onward.config.yaml"]` template to change `post_task_shell: []` to a default commit command:
  ```yaml
  post_task_shell:
    - "git add -A && git commit -m 'onward: completed ${ONWARD_TASK_ID} - ${ONWARD_TASK_TITLE}' --allow-empty"
  ```
- **execution.py**: In `_run_shell_hooks`, set `ONWARD_TASK_ID` and `ONWARD_TASK_TITLE` environment variables before running each shell command. These come from the task artifact metadata. Modify the function signature or use a closure/context to pass the task info through.
- **execution.py**: In `_execute_task_run`, pass the task metadata when calling `_run_shell_hooks` for `post_task_shell` (and `pre_task_shell` for consistency). The env vars should also include `ONWARD_RUN_ID` (already set for the executor subprocess, but not for shell hooks).
- Add or update tests to verify the env vars are set.

# Out of scope

- Making the commit message format configurable beyond what shell variable expansion provides (users can replace the hook entirely)
- GPG signing or other git commit options
- Conditional commit logic (e.g., only commit if there are changes — `--allow-empty` handles this)
- Pre-task commit or stash behavior
- Chunk-level or plan-level commit hooks

# Files to inspect

- `src/onward/scaffold.py` — `DEFAULT_FILES` dict, specifically the `.onward.config.yaml` template (the `hooks:` section around line 69-79)
- `src/onward/execution.py` — `_run_shell_hooks` function (lines ~62-90): currently runs commands with `subprocess.run` using `cwd=root` but doesn't set custom env vars. Also `_execute_task_run` (lines ~262-265): where `pre_shell` and `post_shell` hooks are invoked
- `tests/test_cli_work.py` — existing tests for work command that may need updates for the new default hook

# Implementation notes

- **Environment variables for hooks**: Modify `_run_shell_hooks` to accept an optional `env: dict[str, str] | None` parameter. When provided, merge it with `os.environ` (like `{**os.environ, **env}`) and pass to `subprocess.run`. In `_execute_task_run`, build the env dict:
  ```python
  hook_env = {
      "ONWARD_RUN_ID": run_id,
      "ONWARD_TASK_ID": task_id,
      "ONWARD_TASK_TITLE": str(task.metadata.get("title", "")),
  }
  ```
  Pass this to both `pre_task_shell` and `post_task_shell` calls.
- **Shell variable expansion**: The commit message uses `${ONWARD_TASK_ID}` and `${ONWARD_TASK_TITLE}` which are expanded by the shell since `shell=True` is already used in `subprocess.run`. The env vars just need to be present in the subprocess environment.
- **`--allow-empty`**: Essential because some tasks might not produce file changes (e.g., documentation reviews, config-only changes). Without it, `git commit` would fail and the post-hook would report failure.
- **`git add -A`**: Stages everything including untracked files. This is intentional for the default — users who want more selective staging can replace the hook.
- **Single-quoted commit message**: The YAML uses double quotes for the list item, and the commit message is in single quotes. This prevents YAML from interpreting the `${}` sequences while letting the shell expand them.
- **Test considerations**: Existing tests that use `executor.enabled: false` or `command: "true"` may now hit the default post_task_shell hook. Either update test configs to explicitly clear the hook (`post_task_shell: []`) or ensure the test environment handles git operations gracefully. Since tests usually run with `command: "true"`, the post hook would try to git commit — which may fail in test dirs that aren't git repos. **Recommended**: make test setup configs explicitly set `post_task_shell: []` to avoid interference.

# Acceptance criteria

- `onward init` creates a `.onward.config.yaml` where `hooks.post_task_shell` is a list containing a git commit command (not an empty list)
- The commit command includes `${ONWARD_TASK_ID}` and `${ONWARD_TASK_TITLE}` variable references
- The commit command includes `--allow-empty`
- During `_run_shell_hooks` for post_task_shell, the subprocess environment contains `ONWARD_TASK_ID`, `ONWARD_TASK_TITLE`, and `ONWARD_RUN_ID`
- Existing tests still pass (test configs may need explicit `post_task_shell: []` to avoid git operations in test environments)
- The hook is opt-out: users can set `post_task_shell: []` in their config to disable it

# Handoff notes

This hook creates a 1:1 mapping between Onward task completions and git commits, which is the foundation for the "git history as execution log" pattern. The env var mechanism (`ONWARD_TASK_ID`, `ONWARD_TASK_TITLE`, `ONWARD_RUN_ID`) is reusable for any custom hooks users create. If tests break because of the new default hook, the fix is to add `post_task_shell: []` to test config fixtures — don't remove the default hook to fix tests.
