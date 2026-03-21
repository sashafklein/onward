---
id: "CHUNK-010"
type: "chunk"
plan: "PLAN-003"
project: ""
title: "Migrate command to move artifacts to new root"
status: "open"
description: "Add onward migrate command to move .onward/ contents to a newly configured root"
depends_on:
  - "CHUNK-004"
priority: "medium"
effort: "m"
model: "claude-sonnet-4-5"
created_at: "2026-03-21T16:04:35Z"
updated_at: "2026-03-21T16:04:35Z"
---

# Summary

Add an `onward migrate` command that moves existing `.onward/` artifact contents to a newly configured root location. This gives users a safe, one-command upgrade path when they change `root` or `roots` in their config.

# Scope

- New `onward migrate` subcommand
- Detects the current artifact location (reads old layout from what's on disk vs. new layout from config)
- Moves plans, runs, reviews, templates, prompts, hooks, notes, ongoing.json, index/recent to the new root
- For `roots` config: prompts for which project to migrate into (or accepts `--project`)
- Dry-run mode (`--dry-run`) that prints what would be moved without doing it
- Updates `.gitignore` entries from old root to new root
- Validates that the target directory structure exists (runs scaffold if needed)
- Errors if source and target are the same
- Errors if target already has content (unless `--force`)

# Out of scope

- Migrating between `root` and `roots` (splitting one dir into multiple projects) — that's a manual operation
- Automated config file editing (user sets `root`/`roots` in config first, then runs `migrate`)

# Dependencies

- CHUNK-004 (scaffold must support configurable roots so migrate can ensure target dirs exist)

# Expected files/systems involved

- `src/onward/cli.py` — new `migrate` subparser
- `src/onward/cli_commands.py` — `cmd_migrate` handler
- `src/onward/scaffold.py` — reuse scaffold functions to ensure target dirs
- `tests/test_migrate.py` — migration tests

# Completion criteria

- [ ] `onward migrate --dry-run` prints planned moves without touching disk
- [ ] `onward migrate` moves all artifact subdirectories from old root to new root
- [ ] `.gitignore` is updated with new paths
- [ ] Migrate errors if source and target are the same
- [ ] Migrate errors if target has existing content (without `--force`)
- [ ] `onward migrate --force` overwrites existing content at target
- [ ] After migration, `onward doctor` passes with the new config
- [ ] Test covers `.onward/ → nb/` migration end-to-end

# Notes

- The typical workflow is: (1) user edits `.onward.config.yaml` to set `root: nb`, (2) runs `onward migrate`, (3) artifacts are now under `nb/`.
- The command should be idempotent: running it twice when already migrated is a no-op (source doesn't exist).
