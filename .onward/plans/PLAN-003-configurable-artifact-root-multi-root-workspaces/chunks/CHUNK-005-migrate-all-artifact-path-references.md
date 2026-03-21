---
id: "CHUNK-005"
type: "chunk"
plan: "PLAN-003"
project: ""
title: "Migrate all artifact path references"
status: "open"
description: "Replace every hardcoded .onward/ path construction with WorkspaceLayout method calls"
depends_on:
  - "CHUNK-003"
  - "CHUNK-004"
priority: "high"
effort: "xl"
model: "claude-opus-4-5"
created_at: "2026-03-21T15:46:43Z"
updated_at: "2026-03-21T15:46:43Z"
---

# Summary

The biggest chunk: replace every `root / ".onward/..."` path construction across all source files with calls through `WorkspaceLayout`. After this, artifact storage actually uses the configured root. This also includes threading the layout (or project parameter) through function signatures.

# Scope

- **artifacts.py** (~6 locations): `artifact_glob`, `find_plan_dir`, `load_index`, `index_is_fresh`, `regenerate_indexes`, `_notes_path` — all need a `layout` or `project` parameter
- **execution.py** (~6 locations): `load_ongoing`, `_write_ongoing`, `_prepare_task_run`, `collect_runs_for_target`, `collect_run_records`, `execute_plan_review` — run/review dirs, ongoing.json
- **config.py** (2 locations): `load_artifact_template`, `_load_prompt` — template/prompt lookup with per-project fallback
- **split.py** (1 location): `run_split_model` prompt path
- **cli_commands.py** (~5 locations): `cmd_new_plan` plan dir, `cmd_archive` archive dir, `cmd_review_plan` prompt path, `cmd_split` prompt display
- Thread `WorkspaceLayout` through callers — functions that currently take `root: Path` may need `layout: WorkspaceLayout` or `(root, project)` pairs
- Template/prompt/hook resolution: check project-specific dir first, fall back to shared dir
- Per-project `index.yaml`, `recent.yaml`, `ongoing.json`

# Out of scope

- CLI argument enforcement for `--project` (CHUNK-006)
- Sync path migration (CHUNK-007)
- Test file updates (CHUNK-008)

# Dependencies

- CHUNK-003 (WorkspaceLayout exists)
- CHUNK-004 (scaffold creates the right directories)

# Expected files/systems involved

- `src/onward/artifacts.py`
- `src/onward/execution.py`
- `src/onward/config.py`
- `src/onward/split.py`
- `src/onward/cli_commands.py`
- `src/onward/preflight.py` (error message references)

# Completion criteria

- [ ] Zero remaining `root / ".onward/"` string literals in source files (excluding sync.py, which is CHUNK-007)
- [ ] `artifact_glob` uses `layout.plans_dir(project)`
- [ ] `load_index` / `regenerate_indexes` use `layout.index_path(project)` / `layout.recent_path(project)`
- [ ] `_prepare_task_run` uses `layout.runs_dir(project)`
- [ ] `load_ongoing` / `_write_ongoing` use `layout.ongoing_path(project)`
- [ ] `load_artifact_template` checks project template dir, then shared
- [ ] `_load_prompt` checks project prompts dir, then shared
- [ ] Existing tests still pass with default config (`.onward/` root)

# Notes

This is the largest chunk and may need to be split into tasks per-file. The key design decision is whether functions take `layout: WorkspaceLayout` directly or take `root: Path` + `project: str | None` and construct the layout internally. Prefer passing `layout` to avoid repeated config loading.
