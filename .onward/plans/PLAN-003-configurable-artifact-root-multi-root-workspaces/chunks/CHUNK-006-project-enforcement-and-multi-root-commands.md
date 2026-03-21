---
id: "CHUNK-006"
type: "chunk"
plan: "PLAN-003"
project: ""
title: "Project enforcement and multi-root commands"
status: "open"
description: "Enforce --project on all commands when roots is configured; combined multi-project report"
depends_on:
  - "CHUNK-005"
priority: "high"
effort: "l"
model: "claude-opus-4-5"
created_at: "2026-03-21T15:46:44Z"
updated_at: "2026-03-21T15:46:44Z"
---

# Summary

Wire up `--project` enforcement so that when `roots` is configured, every artifact-touching command requires a project key (or uses `default_project`). Also implement the combined multi-project report.

# Scope

- Add a `require_project_or_default(args, layout)` helper that:
  - If `roots` is NOT configured (single-root), returns `None` (current behavior)
  - If `roots` IS configured and `--project` is given, validates it against `roots` keys
  - If `roots` IS configured and `--project` is missing, checks `default_project` from config
  - If neither is available, errors: `"Multiple projects configured. Use --project <name> (available: ...)"`
- Call this helper at the top of every command that touches artifacts: `new plan`, `new chunk`, `new task`, `new task-batch`, `list`, `show`, `work`, `complete`, `cancel`, `retry`, `next`, `tree`, `report`, `progress`, `recent`, `ready`, `split`, `review-plan`, `archive`, `note`
- Set `project` frontmatter automatically on new artifacts from the resolved project key
- `onward report` without `--project` in multi-root mode: load artifacts from all roots, group by project
- `onward report --project <key>` in multi-root mode: load only from that root
- `onward next` without `--project` in multi-root: pick across all projects (respecting priority)
- ID generation in multi-root: scan all roots for existing IDs to maintain global uniqueness

# Out of scope

- Sync integration (CHUNK-007)
- Tests and docs (CHUNK-008)

# Dependencies

- CHUNK-005 (all path references migrated)

# Expected files/systems involved

- `src/onward/cli_commands.py` — every command handler
- `src/onward/cli.py` — argument definitions (may need to validate `--project` choices dynamically)
- `src/onward/artifacts.py` — multi-root artifact collection, ID generation across roots

# Completion criteria

- [ ] Running any artifact command with `roots` configured and no `--project` produces clear error
- [ ] `--project <key>` is validated against configured roots keys
- [ ] `default_project` in config is used as fallback
- [ ] New artifacts get `project` frontmatter auto-set
- [ ] `onward report` without `--project` shows combined multi-project report with project grouping
- [ ] `onward next` without `--project` selects across all projects
- [ ] IDs remain globally unique across projects
