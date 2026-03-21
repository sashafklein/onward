---
id: "PLAN-003"
type: "plan"
project: ""
title: "Configurable artifact root (multi-root workspaces)"
status: "in_progress"
description: ""
priority: "medium"
model: "claude-opus-4-5"
created_at: "2026-03-21T15:44:36Z"
updated_at: "2026-03-21T16:32:23Z"
---

# Summary

Replace the hardcoded `.onward/` artifact directory with a configurable `root` / `roots` key in `.onward.config.yaml`. This enables visible, syncable artifact directories (e.g. Obsidian-friendly non-dotdirs) and true multi-project workspaces with directory-level separation.

# Problem

1. The `.onward/` dotdir is invisible to tools like Obsidian and skipped by Obsidian Sync. Users need plans visible and syncable via non-dot directories.
2. Multi-project workspaces (e.g., an AI agent managing multiple codebases) need clear directory-level separation, not just `--project` metadata tags.
3. The `--project` flag today is a metadata filter only — it does not affect where artifacts are stored on disk.

# Goals

- Make the artifact root configurable via `root: <path>` (single-project) in `.onward.config.yaml`
- Support `roots: { key: path, ... }` for multi-project workspaces with separate artifact trees
- Preserve full backward compatibility when neither `root` nor `roots` is set (default `.onward/`)
- Enforce `--project <key>` on every artifact-touching command when `roots` is configured
- Combined and per-project `onward report` for multi-root setups
- Per-project template/prompt/hook overrides with shared fallback

# Non-goals

- Changing the config file location (`.onward.config.yaml` stays at workspace root)
- Cross-workspace federation (multiple git repos sharing plans)
- Renaming or removing the `--project` metadata field on artifacts
- Changing artifact ID format or introducing per-project ID namespaces (IDs remain globally unique)

# End state

- [ ] `root: nb` in config causes all artifacts to live under `./nb/plans/`, `./nb/runs/`, etc.
- [ ] `roots: { nb: ./nb, clawtree: ./clawtree }` creates two independent artifact trees
- [ ] `onward init` scaffolds all configured root directories
- [ ] Every command errors clearly when `roots` is set but `--project` is missing
- [ ] `onward report` without `--project` shows a combined multi-project report
- [ ] `onward report --project nb` scopes to a single project
- [ ] `onward doctor` validates root/roots config and checks all directories exist
- [ ] Templates, prompts, and hooks resolve per-project first, then shared fallback
- [ ] All existing tests pass with the default `.onward/` root
- [ ] New tests cover single custom root and multi-root scenarios

# Context

There are ~30+ hardcoded `.onward/` path constructions across 8 source files: `artifacts.py`, `config.py`, `scaffold.py`, `cli_commands.py`, `execution.py`, `sync.py`, `split.py`, `preflight.py`. Each must resolve through a central path helper.

The current `--project` flag is purely a metadata filter applied at query time. This plan upgrades it to also control which artifact root directory is used when `roots` is configured.

Key files and their `.onward/` usage:
- `scaffold.py`: `DEFAULT_DIRECTORIES`, `DEFAULT_FILES`, `GITIGNORE_LINES`, `REQUIRED_PATHS`, `_is_workspace_root`
- `config.py`: `load_workspace_config`, `load_artifact_template`, `_load_prompt`, `validate_config_contract_issues`
- `artifacts.py`: `artifact_glob`, `find_plan_dir`, `load_index`, `regenerate_indexes`, `_notes_path`
- `cli_commands.py`: `cmd_doctor`, `cmd_new_plan`, `cmd_archive`, `cmd_review_plan`, `cmd_report`
- `execution.py`: `load_ongoing`, `_write_ongoing`, `_prepare_task_run`, `collect_runs_for_target`, `execute_plan_review`
- `sync.py`: `parse_sync_settings`, `plans_dir`, `ensure_branch_worktree`, `git_commit_plans_if_changed`
- `split.py`: `run_split_model` prompt path

# Proposed approach

## Phase 1: Core path resolution layer

Introduce a `WorkspaceLayout` dataclass (or similar) in `config.py` that encapsulates all artifact path resolution:

```python
@dataclass
class WorkspaceLayout:
    workspace_root: Path
    roots: dict[str, Path]      # project_key -> absolute artifact root
    default_project: str | None # from config `default_project` key

    @classmethod
    def from_config(cls, root: Path, config: dict) -> "WorkspaceLayout":
        ...

    def artifact_root(self, project: str | None = None) -> Path:
        """Resolve the artifact root for a project (or the only root in single-root mode)."""
        ...

    def plans_dir(self, project: str | None = None) -> Path:
        return self.artifact_root(project) / "plans"

    def runs_dir(self, project: str | None = None) -> Path:
        return self.artifact_root(project) / "runs"

    # ... reviews_dir, templates_dir, prompts_dir, hooks_dir, notes_dir, sync_dir
    # ... ongoing_path, index_path, recent_path
```

Config schema additions to `CONFIG_TOP_LEVEL_KEYS`:
- `root` — string path, default `.onward`
- `roots` — mapping of `{ key: path }`
- `default_project` — string, optional

Validation rules:
- `root` and `roots` are mutually exclusive (doctor error if both set)
- When `roots` is set, each value must be a non-empty string path
- When `root` is a relative path, it resolves relative to workspace root
- `default_project` must match a key in `roots` if set

## Phase 2: Scaffold & init

Update `scaffold.py`:
- `DEFAULT_DIRECTORIES` becomes a function that accepts an artifact root path
- `DEFAULT_FILES` keys are parameterized by root
- `GITIGNORE_LINES` adapts to configured root(s)
- `REQUIRED_PATHS` adapts
- `_is_workspace_root` checks the configured root(s), not hardcoded `.onward`
- `cmd_init` iterates over all configured roots when `roots` is set

Update `cmd_doctor`:
- Validate `root`/`roots` config
- Check all configured directories exist
- Remove the old "unsupported config key 'path'" rejection and replace with `root`/`roots` awareness

## Phase 3: Artifact path migration

Replace every `root / ".onward/..."` construction with `layout.xxx_dir(project)` calls:

- `artifacts.py`: `artifact_glob`, `find_plan_dir`, `load_index`, `index_is_fresh`, `regenerate_indexes`, `_notes_path`
- `execution.py`: `load_ongoing`, `_write_ongoing`, `_prepare_task_run`, `collect_runs_for_target`, `collect_run_records`, `execute_plan_review`
- `config.py`: `load_artifact_template`, `_load_prompt`
- `split.py`: prompt path resolution
- `cli_commands.py`: `cmd_new_plan`, `cmd_archive`, `cmd_review_plan`, prompt path in `cmd_split`

For template/prompt/hook resolution: check project-specific dir first, fall back to a shared location. The shared location is:
- When `root` is set: the configured root (only one)
- When `roots` is set: a `shared` key in roots, or a top-level `.onward/` fallback, or error if not found

## Phase 4: --project enforcement

When `roots` is configured:
- Every command that touches artifacts must receive `--project <key>` (or use `default_project` from config)
- If neither is provided, error: `"Multiple projects configured. Use --project <name> (available: nb, clawtree)"`
- The `--project` value must match a key in `roots`
- `project` frontmatter on new artifacts is auto-set from `--project`

Commands affected: `new plan`, `new chunk`, `new task`, `new task-batch`, `list`, `show`, `work`, `complete`, `cancel`, `retry`, `next`, `tree`, `report`, `progress`, `recent`, `ready`, `split`, `review-plan`, `archive`, `note`, `doctor`

When `root` (single) is configured, `--project` remains an optional metadata filter (current behavior).

## Phase 5: Multi-project indexes and ongoing state

Each project root gets its own:
- `index.yaml` (under `<root>/plans/index.yaml`)
- `recent.yaml` (under `<root>/plans/recent.yaml`)
- `ongoing.json` (under `<root>/ongoing.json`)

Index operations (`regenerate_indexes`, `load_index`, `artifacts_from_index_or_collect`) need a project parameter to know which root to use.

For combined views (e.g., `onward report` without `--project`), load and merge indexes from all roots.

## Phase 6: Sync integration

`sync.py` must resolve `plans_dir` through the layout. Sync currently assumes a single `.onward/plans` directory. Options:
- When `roots` is set, `sync push/pull` requires `--project` (sync one project at a time)
- Or sync all projects in sequence

The `worktree_path` default (`.onward/sync`) must adapt to the configured root.

## Phase 7: Migration command

Add `onward migrate` to move existing `.onward/` contents to a newly configured root:
- User edits config to set `root: nb`, then runs `onward migrate`
- Command detects the old layout (what's on disk) vs. new layout (from config)
- Moves all artifact subdirectories (plans, runs, reviews, templates, prompts, hooks, notes, ongoing.json, index/recent)
- `--dry-run` prints what would move without touching disk
- `--force` overwrites if target already has content
- Updates `.gitignore` entries from old root to new root
- Idempotent: no-op if source doesn't exist
- For multi-root (`roots`), accepts `--project` to target a specific project root

## Phase 8: Tests and documentation

- Update all tests that construct `.onward/` paths to use a helper or parameterize
- Add test cases for: single custom root, multi-root, missing --project error, combined report
- Update `AGENTS.md`, `INSTALLATION.md`, `README.md`, `AI_OPERATOR.md` to document the new config keys
- Update scaffold default config template to show `root` as a commented-out option

# Key artifacts

- New config keys: `root`, `roots`, `default_project` in `.onward.config.yaml`
- New class: `WorkspaceLayout` in `config.py`
- New command: `onward migrate` for moving artifacts to a new root
- Modified: every source file that constructs `.onward/` paths
- Modified: every test file that assumes `.onward/` paths

# Acceptance criteria

1. `onward doctor` passes with `root: .onward` (backward compatible)
2. `onward doctor` passes with `root: plans` (non-hidden directory)
3. `onward doctor` passes with `roots: {nb: ./nb, other: ./other}`
4. `onward new plan "test" --project nb` creates plan in correct project dir when using `roots`
5. `onward work TASK-001 --project nb` resolves task in correct project dir
6. Commands without `--project` error clearly when `roots` is configured (unless `default_project` is set)
7. `onward report` without `--project` shows combined multi-project view
8. `onward migrate` moves `.onward/` contents to new root location
9. All existing tests pass
10. New tests cover single custom root, multi-root, and migration scenarios
11. Template/prompt lookups check project dir first, then fall back

# Notes

- This is a large cross-cutting refactor. The `WorkspaceLayout` abstraction is the linchpin — getting it right simplifies everything downstream.
- The `ongoing.json` file needs careful handling in multi-root: each project needs its own so concurrent runs in different projects don't collide.
- ID uniqueness across projects is maintained by the existing counter-based ID generation (which scans all known artifacts). In multi-root mode, the counter must scan across all roots.
