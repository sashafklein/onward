---
id: "TASK-012"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-003"
project: ""
title: "Define WorkspaceLayout dataclass with path resolution methods"
status: "in_progress"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "m"
depends_on: []
files: []
acceptance: []
created_at: "2026-03-21T15:49:12Z"
updated_at: "2026-03-21T16:17:09Z"
run_count: 1
---

# Context

Foundation for all configurable-root work in PLAN-003. Every other task in this plan depends on this dataclass existing. It creates the single abstraction that replaces all hardcoded `.onward/` path construction throughout the codebase. The class must support three modes: default (`.onward`), single custom root (`root: nb`), and multi-root (`roots: {a: ..., b: ...}`).

# Scope

- Create a `WorkspaceLayout` dataclass in `src/onward/config.py` (or a new `src/onward/layout.py` if config.py is already large).
- Class fields: `workspace_root: Path`, `roots: dict[str, Path]` (project key -> artifact root path), `default_project: str | None`.
- Factory method: `from_config(root: Path, config: dict) -> WorkspaceLayout` — reads `root`, `roots`, `default_project` from config; falls back to `{None: root / ".onward"}` when none are set.
- Path resolution methods (all accept `project: str | None = None`):
  - `artifact_root(project)` — base artifact directory for the project
  - `plans_dir(project)` — `artifact_root / "plans"`
  - `runs_dir(project)` — `artifact_root / "runs"`
  - `reviews_dir(project)` — `artifact_root / "reviews"`
  - `templates_dir(project)` — `artifact_root / "templates"`
  - `prompts_dir(project)` — `artifact_root / "prompts"`
  - `hooks_dir(project)` — `artifact_root / "hooks"`
  - `notes_dir(project)` — `artifact_root / "notes"`
  - `sync_dir(project)` — `artifact_root / "sync"`
  - `ongoing_path(project)` — `artifact_root / "ongoing.json"`
  - `index_path(project)` — `artifact_root / "index.json"`
  - `recent_path(project)` — `artifact_root / "recent.json"`
  - `archive_dir(project)` — `artifact_root / "archive"`
- Property: `is_multi_root: bool` — `len(roots) > 1`.
- Method: `all_project_keys() -> list[str | None]` — returns all configured project keys (or `[None]` in single-root mode).

# Out of scope

- Config validation logic (TASK-013).
- Wiring WorkspaceLayout into existing modules (TASK-018 through TASK-021).
- Template/prompt fallback logic (TASK-022).

# Files to inspect

- `src/onward/config.py` — existing config loading, `CONFIG_TOP_LEVEL_KEYS`, `load_config`, `validate_config_contract_issues`

# Implementation notes

- Single-root mode stores `{None: Path(".onward")}` in `roots` dict so all methods work uniformly — callers pass `project=None`.
- When `root` is set in config (e.g. `root: nb`), store as `{None: workspace_root / "nb"}`.
- When `roots` is set (e.g. `roots: {frontend: .fe-plans, backend: .be-plans}`), each key maps to its path. `project=None` resolves to `default_project` if set.
- All directory methods should resolve relative to `workspace_root` if the root path is relative.
- Raise `ValueError` if `project` is required but not provided (multi-root without default).

# Acceptance criteria

- `WorkspaceLayout` class exists with all listed methods.
- `from_config` with no root/roots config returns layout pointing at `.onward`.
- `from_config` with `root: nb` returns layout where `artifact_root()` points at `<workspace>/nb`.
- `from_config` with `roots: {a: .a, b: .b}` returns layout where `artifact_root("a")` points at `<workspace>/.a`.
- `is_multi_root` returns `False` for default/single, `True` for multi.
- All directory methods return correct subdirectory paths.

# Handoff notes

- This is the foundational building block. Once merged, TASK-013 (validation), TASK-014 (tests), and all migration tasks can proceed in parallel.
- Design decision: whether to put this in `config.py` or a new `layout.py` depends on config.py size; prefer a new file if config.py exceeds ~400 lines.
