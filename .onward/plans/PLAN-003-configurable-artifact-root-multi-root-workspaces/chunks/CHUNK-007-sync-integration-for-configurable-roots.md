---
id: "CHUNK-007"
type: "chunk"
plan: "PLAN-003"
project: ""
title: "Sync integration for configurable roots"
status: "in_progress"
description: "Update sync.py to resolve plans_dir and worktree paths through WorkspaceLayout"
depends_on:
- "CHUNK-005"
priority: "medium"
effort: "m"
model: "claude-sonnet-4-5"
created_at: "2026-03-21T15:46:46Z"
updated_at: "2026-03-21T18:04:47Z"
---

# Summary

Make `onward sync push/pull/status` work with configurable roots. Sync has its own set of `.onward/plans` references and a `worktree_path` default that need updating.

# Scope

- Replace all `root / ".onward" / "plans"` and `wt / ".onward" / "plans"` in sync.py with layout-based paths
- Update `parse_sync_settings` default `worktree_path` to use configured root
- Update `plans_dir()` helper to use layout
- Update `ensure_branch_worktree`, `ensure_repo_clone`, `remote_plans_path` to use configured root(s)
- Update `git_commit_plans_if_changed` git add path to use configured root
- When `roots` is configured, `sync push/pull` requires `--project` (sync one project at a time)
- Update `cmd_sync_push`, `cmd_sync_pull`, `cmd_sync_status` to accept and use project parameter

# Out of scope

- Syncing multiple projects in a single command (future work)
- Changing sync protocol or remote structure

# Dependencies

- CHUNK-005 (path migration done for other files)

# Expected files/systems involved

- `src/onward/sync.py` — all path references (~10 locations)
- `src/onward/cli_commands.py` — sync command handlers
- `src/onward/cli.py` — add `--project` to sync subcommands

# Completion criteria

- [ ] Zero remaining hardcoded `.onward/plans` in sync.py
- [ ] `onward sync push --project nb` syncs only that project's plans
- [ ] `worktree_path` default adapts to configured root
- [ ] Existing sync tests pass with default config
- [ ] New test: sync with custom root
