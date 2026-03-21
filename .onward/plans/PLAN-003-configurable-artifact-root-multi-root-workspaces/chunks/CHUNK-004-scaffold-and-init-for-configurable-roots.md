---
id: "CHUNK-004"
type: "chunk"
plan: "PLAN-003"
project: ""
title: "Scaffold and init for configurable roots"
status: "completed"
description: "Update scaffold.py and cmd_init/cmd_doctor to create and validate configurable root directories"
depends_on:
- "CHUNK-003"
priority: "high"
effort: "m"
model: "claude-opus-4-5"
created_at: "2026-03-21T15:46:42Z"
updated_at: "2026-03-21T17:02:51Z"
---

# Summary

Make `onward init` and `onward doctor` work with configurable `root`/`roots`. After this chunk, `onward init` creates the right directory structure based on config, and `onward doctor` validates it.

# Scope

- Parameterize `DEFAULT_DIRECTORIES` to accept an artifact root path instead of hardcoding `.onward/`
- Parameterize `DEFAULT_FILES` keys by root (config file stays at workspace root; everything else under the configured root(s))
- Update `GITIGNORE_LINES` to use configured root paths
- Update `REQUIRED_PATHS` to use configured root paths
- Update `_is_workspace_root` to check configured root(s)
- Update `cmd_init` to iterate over all configured roots when `roots` is set, scaffolding each
- Update `cmd_doctor` to validate root/roots config keys and check directory existence
- Remove the old `"unsupported config key 'path'"` rejection in `validate_config_contract_issues`

# Out of scope

- Changing how other commands resolve paths (CHUNK-005)
- CLI --project enforcement (CHUNK-006)

# Dependencies

- CHUNK-003 (WorkspaceLayout must exist)

# Expected files/systems involved

- `src/onward/scaffold.py` — parameterize all path lists and functions
- `src/onward/cli_commands.py` — `cmd_init`, `cmd_doctor` updates
- `src/onward/config.py` — remove old `path` key rejection
- `tests/` — tests for init with custom roots

# Completion criteria

- [ ] `onward init` with default config creates `.onward/` tree (backward compatible)
- [ ] `onward init` with `root: nb` creates `nb/plans/`, `nb/templates/`, etc.
- [ ] `onward init` with `roots: { a: ./a, b: ./b }` creates both trees
- [ ] `onward doctor` passes with valid `root` config
- [ ] `onward doctor` errors when both `root` and `roots` are set
- [ ] `_is_workspace_root` works with custom root
- [ ] `.gitignore` entries use configured root paths
