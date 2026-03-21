---
id: "TASK-016"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-004"
project: ""
title: "Update cmd_init to scaffold configurable roots"
status: "in_progress"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "s"
depends_on:
- "TASK-015"
files: []
acceptance: []
created_at: "2026-03-21T15:49:19Z"
updated_at: "2026-03-21T16:53:26Z"
run_count: 1
---

# Context

`cmd_init` must create the artifact directory tree under whatever root(s) the user has configured, not just `.onward/`. This is the first user-visible behavior change in the configurable-root feature.

# Scope

- In `cmd_init`, after writing `.onward.config.yaml` (which always goes at workspace root), load the config and build a `WorkspaceLayout`.
- Iterate over all roots in the layout (`layout.all_project_keys()`).
- For each root, call `default_directories(artifact_root)` and `default_files(artifact_root)` to create the directory tree and default files.
- Update gitignore generation to include lines for all configured roots.
- The config file (`.onward.config.yaml`) itself is always created at workspace root regardless of root setting.

# Out of scope

- Parameterizing scaffold functions (TASK-015 — already done).
- Doctor validation (TASK-017).
- Multi-root interactive setup or prompts.

# Files to inspect

- `src/onward/cli_commands.py` — `cmd_init` function
- `src/onward/scaffold.py` — `default_directories`, `default_files`, `gitignore_lines`

# Implementation notes

- On first `onward init`, no config file exists yet, so the layout defaults to `.onward` — preserving current behavior.
- If a user creates `.onward.config.yaml` with `root: nb` before running `onward init`, init should scaffold under `nb/`.
- For re-init (already initialized workspace): skip existing directories/files, only create missing ones.
- Config template content itself is updated in TASK-031 (not this task).

# Acceptance criteria

- `onward init` with no config creates `.onward/` tree as before.
- `onward init` with `root: nb` in existing config creates `nb/` tree with all subdirectories.
- `onward init` with `roots: {a: .a, b: .b}` creates both `.a/` and `.b/` trees.
- `.onward.config.yaml` is always at workspace root in all cases.

# Handoff notes

- Test this manually with `onward init` in a temp directory with various configs.
- TASK-031 will update the default config template to show the `root` option.
