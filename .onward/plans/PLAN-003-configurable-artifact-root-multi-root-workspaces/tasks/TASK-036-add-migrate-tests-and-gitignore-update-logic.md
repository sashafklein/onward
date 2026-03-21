---
id: "TASK-036"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-010"
project: ""
title: "Add migrate tests and gitignore update logic"
status: "completed"
description: "Tests for migrate command and logic to update .gitignore entries from old to new root"
human: false
model: "claude-sonnet-4-5"
effort: "s"
depends_on:
- "TASK-035"
files:
- "src/onward/cli_commands.py"
- "src/onward/scaffold.py"
- "tests/test_migrate.py"
acceptance:
- "Test covers .onward/ → nb/ migration end-to-end"
- "Test covers --dry-run mode"
- "Test covers --force overwrite"
- ".gitignore entries updated from old root paths to new root paths"
- "onward doctor passes after migration"
created_at: "2026-03-21T16:05:06Z"
updated_at: "2026-03-21T18:18:43Z"
run_count: 1
---

# Context

This task completes TASK-035 by adding comprehensive test coverage for the `onward migrate` command and implementing the .gitignore update logic that was part of the migration spec but not yet implemented.

# Scope

- Implement `_update_gitignore_for_migration` helper function in `cli_commands.py` to update .gitignore entries from old root to new root
- Create `tests/test_migrate.py` with comprehensive test coverage:
  - Basic migration from .onward/ to custom root (e.g., nb/)
  - Dry-run mode (--dry-run)
  - Force overwrite (--force)
  - Multi-root mode with --project flag
  - Error cases (source == target, target has content, missing project)
  - .gitignore updates
  - onward doctor passing after migration
  - Idempotent behavior
  - Content preservation

# Out of scope

- Splitting one root into multiple projects (manual operation)
- Migration from one custom root to another (only .onward/ → custom root is automated)
- Backup functionality (--backup flag suggested in TASK-035 handoff notes)

# Files to inspect

- `src/onward/cli_commands.py` — cmd_migrate and _update_gitignore_for_migration
- `tests/test_migrate.py` — comprehensive test suite
- `tests/test_cli_init_doctor.py` — reference for test patterns

# Implementation notes

- The `_update_gitignore_for_migration` helper function:
  - Reads existing .gitignore
  - Creates a mapping from old gitignore entries to new ones using `gitignore_lines()`
  - Replaces old entries with new entries (not duplicating)
  - Adds any new entries that weren't in the old set
  - Creates .gitignore if it doesn't exist

- Tests cover all major scenarios:
  - 11 comprehensive test cases
  - All edge cases from acceptance criteria
  - Tests verify filesystem state, output messages, and error conditions
  - One test initially failed due to trying to read a plan directory as a file (plans are directories with PLAN.md inside) — fixed by accessing the PLAN.md file

- Migration logic properly handles:
  - Moving directories with `shutil.move()` or `shutil.copytree()` + removal
  - Merging contents when target exists (with --force)
  - Removing empty source directories after migration
  - Preserving file metadata with `shutil.copy2()`

# Acceptance criteria

✅ Test covers .onward/ → nb/ migration end-to-end (test_migrate_basic_custom_root)
✅ Test covers --dry-run mode (test_migrate_dry_run)
✅ Test covers --force overwrite (test_migrate_force_overwrite)
✅ .gitignore entries updated from old root paths to new root paths (_update_gitignore_for_migration function, test_migrate_updates_gitignore_entries)
✅ onward doctor passes after migration (test_migrate_basic_custom_root)
✅ All 11 tests pass
✅ No regressions in test_cli_init_doctor.py (21 tests pass)

# Handoff notes

- TASK-035 was marked completed but the implementation was missing — both TASK-035 and TASK-036 were actually implemented together in this work session
- The migrate command is now fully functional with:
  - CLI parser in `src/onward/cli.py` (added migrate subparser, imported cmd_migrate)
  - Implementation in `src/onward/cli_commands.py` (cmd_migrate and _update_gitignore_for_migration)
  - Comprehensive tests in `tests/test_migrate.py` (11 test cases)

- Future enhancements from TASK-035 handoff notes:
  - Add migration path for splitting one root into multiple projects
  - Consider adding --backup flag to create tarball before migration
  - Handle edge cases for users who have already partially migrated

- The migration command enables the full multi-root workspace feature by providing a safe upgrade path for existing .onward/ workspaces
