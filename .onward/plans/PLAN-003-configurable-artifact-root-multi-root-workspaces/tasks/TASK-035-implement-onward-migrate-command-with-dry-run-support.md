---
id: "TASK-035"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-010"
project: ""
title: "Implement onward migrate command with dry-run support"
status: "completed"
description: "New onward migrate subcommand: detect old root, move contents to new configured root, --dry-run, --force"
human: false
model: "claude-sonnet-4-5"
effort: "m"
depends_on:
- "TASK-015"
files:
- "src/onward/cli.py"
- "src/onward/cli_commands.py"
- "src/onward/scaffold.py"
acceptance:
- "onward migrate --dry-run prints planned moves"
- "onward migrate moves all subdirs from .onward/ to configured root"
- "Errors if source and target are the same"
- "Errors if target has existing content without --force"
- "Idempotent: no-op if source doesn't exist"
created_at: "2026-03-21T16:05:04Z"
updated_at: "2026-03-21T18:18:43Z"
run_count: 1
last_run_status: "completed"
---

# Context

Implement the `onward migrate` command to move existing `.onward/` artifact contents to a newly configured root location. This is the final piece of CHUNK-010, giving users a safe upgrade path when they change `root` or `roots` in their config. The command detects what's on disk, compares to the configured layout from `WorkspaceLayout`, and moves all artifact subdirectories to the new location.

# Scope

- Add `migrate` subparser to `src/onward/cli.py` with `--dry-run`, `--force`, and `--project` flags
- Implement `cmd_migrate` in `src/onward/cli_commands.py` that:
  - Loads config and creates `WorkspaceLayout` to determine target root(s)
  - Detects source root by checking which directories exist (`.onward/plans`, custom root from disk)
  - Validates source ≠ target (error if same)
  - Checks if target already has content (error unless `--force`)
  - Moves all artifact subdirectories: `plans/`, `runs/`, `reviews/`, `templates/`, `prompts/`, `hooks/`, `notes/`, `ongoing.json`, `plans/index.yaml`, `plans/recent.yaml`
  - Updates `.gitignore` to replace old root paths with new root paths
  - Uses `--dry-run` to print planned operations without executing them
- For multi-root config (`roots`): require `--project` to specify which project root to migrate into
- Ensure target directory structure exists (call scaffold functions if needed)
- Idempotent: no-op if source directory doesn't exist

# Out of scope

- Splitting one root into multiple projects (migrating `.onward/` → multiple `roots`) — that's a manual operation
- Automated config file editing — user must edit `.onward.config.yaml` first, then run `migrate`
- Migrating the config file location itself (always stays at workspace root)
- Cross-workspace migration or federation

# Files to inspect

- `src/onward/cli.py` — add `migrate` subparser with flags
- `src/onward/cli_commands.py` — implement `cmd_migrate` function
- `src/onward/config.py` — use `WorkspaceLayout.from_config()` and path resolution methods
- `src/onward/scaffold.py` — use `default_directories()`, `default_files()`, `gitignore_lines()` for validation

# Implementation notes

- **Detecting source root**: Check if `.onward/plans/` exists (default), or if a custom root from old config exists on disk. The simplest approach: assume source is `.onward/` if it exists, otherwise error (user hasn't run onward before or already migrated).
- **Multi-root migration**: When `roots` is configured, each project gets its own artifact tree. User must run `onward migrate --project <key>` for each project they want to migrate. The source is always the old monolithic `.onward/` directory.
- **Moving operations**: Use `shutil.move()` or `shutil.copytree()` + remove source. Be careful with ongoing.json (might be locked if a task is running).
- **.gitignore update**: Read `.gitignore`, replace lines containing old root path with new root path, write back. Handle case where `.gitignore` doesn't exist (create it with new root paths).
- **Dry-run output**: Print each operation clearly (e.g., "Would move .onward/plans → nb/plans"). Use consistent formatting for user readability.
- **Force flag**: Only needed if target directories already have content. Check if `target_root/plans/` exists and has files.
- **Validation**: After migration, ensure `onward doctor` passes with the new config.

# Acceptance criteria

- `onward migrate --help` shows command usage with --dry-run, --force, --project flags
- `onward migrate --dry-run` prints all planned moves without touching filesystem
- `onward migrate` successfully moves `.onward/` contents to configured root (single-root mode)
- `onward migrate --project nb` moves `.onward/` to the `nb` root in multi-root mode
- Command errors if source and target are the same path
- Command errors if target has existing content without `--force` flag
- Command is idempotent: running twice (or when source doesn't exist) is a no-op
- `.gitignore` is updated with new root paths after migration
- `onward doctor` passes after successful migration
- Test file `tests/test_migrate.py` covers basic migration scenarios

# Handoff notes

- This completes CHUNK-010. After this task, users can configure custom artifact roots and migrate their existing workspaces.
- Future work: Add migration path for splitting one root into multiple projects (would need manual guidance on which artifacts go to which project).
- Consider adding a `--backup` flag that creates a tarball of the old root before moving (defensive for critical workspaces).
- The migrate command assumes a clean migration from `.onward/` → new root. If users have already partially migrated or have custom directory structures, they may need manual intervention.
