---
id: "TASK-022"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-005"
project: ""
title: "Implement per-project template/prompt/hook fallback"
status: "open"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "m"
depends_on: ["TASK-020"]
files: []
acceptance: []
created_at: "2026-03-21T15:49:33Z"
updated_at: "2026-03-21T15:49:33Z"
---

# Context

In multi-root mode, each project directory can have its own `templates/`, `prompts/`, and `hooks/` subdirectories for project-specific customization. If a file isn't found in the project-specific directory, it should fall back to a shared location.

# Scope

- Update `load_artifact_template` to implement fallback:
  1. Check `layout.templates_dir(project)` for the requested template.
  2. If not found, check the shared fallback location (`.onward/templates/` or the first root's templates dir).
  3. If still not found, use the built-in default.
- Apply the same fallback pattern to `_load_prompt`.
- Apply the same fallback pattern to hook resolution (pre/post hooks in `execution.py` or wherever hooks are loaded).
- Document the lookup order in a docstring or inline comment.
- The shared fallback directory: in multi-root mode, `.onward/` always exists as a fallback (even if it's not a configured root). Alternatively, define the first root as the fallback.

# Out of scope

- Creating the WorkspaceLayout class (TASK-012).
- Basic template/prompt path migration (TASK-020 — already done).
- Per-project config overrides beyond templates/prompts/hooks.

# Files to inspect

- `src/onward/config.py` — `load_artifact_template`, `_load_prompt`
- `src/onward/execution.py` — hook loading if applicable
- `src/onward/preflight.py` — if hooks are loaded here

# Implementation notes

- Fallback order: project-specific → shared `.onward/` → built-in default. This mirrors how many build tools handle config inheritance.
- In single-root mode, there's no fallback — the one root is both project-specific and shared.
- `.onward/` should always be created by `onward init` even in multi-root mode, to serve as the shared fallback for templates/prompts/hooks.
- Consider a helper function `resolve_with_fallback(layout, project, subdir, filename)` to DRY the logic.
- Hook files (pre-work, post-work) follow the same pattern.

# Acceptance criteria

- Project-specific template in `<project_root>/templates/task.md` is used over shared one.
- Missing project-specific template correctly falls back to `.onward/templates/task.md`.
- Same fallback works for prompts and hooks.
- Single-root mode behavior is unchanged.
- Lookup order is documented in code.

# Handoff notes

- Test with a multi-root config where one project has a custom `task.md` template and the other doesn't — verify the right template is used for each.
