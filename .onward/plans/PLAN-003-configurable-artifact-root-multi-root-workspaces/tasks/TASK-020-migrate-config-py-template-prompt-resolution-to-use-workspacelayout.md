---
id: "TASK-020"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-005"
project: ""
title: "Migrate config.py template/prompt resolution to use WorkspaceLayout"
status: "open"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "s"
depends_on: ["TASK-012"]
files: []
acceptance: []
created_at: "2026-03-21T15:49:31Z"
updated_at: "2026-03-21T15:49:31Z"
---

# Context

`load_artifact_template` and `_load_prompt` in `config.py` hardcode `.onward/templates/` and `.onward/prompts/` paths. These must use `WorkspaceLayout` to resolve the correct directories.

# Scope

- Update `load_artifact_template` to accept a `layout` parameter and use `layout.templates_dir(project)` instead of hardcoded `.onward/templates/`.
- Update `_load_prompt` to accept a `layout` parameter and use `layout.prompts_dir(project)` instead of hardcoded `.onward/prompts/`.
- Provide backward-compatible defaults so callers not yet updated still work (layout defaults to `.onward`).
- Update any other template/prompt path construction in config.py.

# Out of scope

- Per-project fallback logic (TASK-022 — builds on this).
- Migrating callers in cli_commands.py (TASK-021).
- Config validation changes (TASK-013).

# Files to inspect

- `src/onward/config.py` — `load_artifact_template`, `_load_prompt`, any other `.onward/templates` or `.onward/prompts` references

# Implementation notes

- `load_artifact_template` is called when creating new plans, chunks, tasks. It reads from `templates/plan.md`, `templates/chunk.md`, `templates/task.md`.
- `_load_prompt` is called for split and review operations. It reads from `prompts/split.md`, `prompts/review.md`, etc.
- Both functions currently construct paths like `root / ".onward" / "templates" / filename`. Replace with `layout.templates_dir(project) / filename`.
- Keep default behavior: when `layout=None`, construct a default layout internally so existing callers aren't broken.

# Acceptance criteria

- `load_artifact_template` uses `layout.templates_dir(project)` for path resolution.
- `_load_prompt` uses `layout.prompts_dir(project)` for path resolution.
- Default behavior (no layout passed) still resolves to `.onward/templates/` and `.onward/prompts/`.
- Existing tests that call these functions still pass.

# Handoff notes

- TASK-022 builds on this to add per-project fallback: check project-specific dir, then shared dir.
- TASK-021 will update callers in split.py and cli_commands.py to pass the layout.
