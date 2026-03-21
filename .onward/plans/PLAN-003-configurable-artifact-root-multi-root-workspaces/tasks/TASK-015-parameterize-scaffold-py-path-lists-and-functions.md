---
id: "TASK-015"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-004"
project: ""
title: "Parameterize scaffold.py path lists and functions"
status: "in_progress"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "m"
depends_on:
- "TASK-012"
files: []
acceptance: []
created_at: "2026-03-21T15:49:18Z"
updated_at: "2026-03-21T16:47:29Z"
run_count: 1
---

# Context

`scaffold.py` has `DEFAULT_DIRECTORIES`, `DEFAULT_FILES`, `GITIGNORE_LINES`, and `REQUIRED_PATHS` all hardcoded with `.onward/` prefixes. These must become parameterized so the init flow and doctor can work with any configured artifact root.

# Scope

- Convert `DEFAULT_DIRECTORIES` from a list constant to a function `default_directories(artifact_root: str) -> list[str]` that replaces `.onward` with the given root.
- Similarly convert `DEFAULT_FILES` keys to `default_files(artifact_root: str) -> dict[str, str]`.
- Convert `GITIGNORE_LINES` to `gitignore_lines(artifact_root: str) -> list[str]`.
- Convert `REQUIRED_PATHS` to `required_paths(artifact_root: str) -> list[str]`.
- Update `_is_workspace_root` to check the configured root (via layout or parameter), not hardcoded `.onward`.
- Update `require_workspace` to accept a layout parameter or root string and check the right directory.
- Ensure all internal callers in scaffold.py use the new functions.

# Out of scope

- Updating cmd_init to loop over multiple roots (TASK-016).
- Updating cmd_doctor to use parameterized paths (TASK-017).
- Changing the config template content (TASK-031).

# Files to inspect

- `src/onward/scaffold.py` — `DEFAULT_DIRECTORIES`, `DEFAULT_FILES`, `GITIGNORE_LINES`, `REQUIRED_PATHS`, `_is_workspace_root`, `require_workspace`

# Implementation notes

- Keep the old constants as computed defaults: `DEFAULT_DIRECTORIES = default_directories(".onward")` so any code that still references the constant works during migration.
- `_is_workspace_root` currently checks for `.onward` directory and `.onward.config.yaml`. The config file check stays at workspace root always; only the directory check should use the configured root.
- `require_workspace` is called from many command handlers. Its signature change must be backward-compatible (default parameter) to avoid breaking all callers at once.
- The `.onward.config.yaml` path itself never changes — it always lives at workspace root.

# Acceptance criteria

- `default_directories(".onward")` returns the same list as the old `DEFAULT_DIRECTORIES` constant.
- `default_directories("nb")` returns paths under `nb/` instead of `.onward/`.
- `_is_workspace_root` with a custom root checks for that root directory.
- `require_workspace` with default args still works for existing callers.
- All existing scaffold tests pass.

# Handoff notes

- TASK-016 will use these parameterized functions to scaffold under configurable roots.
- TASK-017 will use `required_paths(root)` for doctor checks.
