---
id: "TASK-017"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-004"
project: ""
title: "Update cmd_doctor for root/roots validation"
status: "completed"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "s"
depends_on:
- "TASK-013"
files: []
acceptance: []
created_at: "2026-03-21T15:49:20Z"
updated_at: "2026-03-21T17:03:07Z"
run_count: 1
last_run_status: "completed"
---

# Context

`onward doctor` should validate the new config keys and verify that configured artifact root directories exist on disk with the expected subdirectory structure. This extends the existing doctor checks to be root-aware.

# Scope

- Build a `WorkspaceLayout` from the loaded config in `cmd_doctor`.
- For each project root in the layout, check that the artifact root directory exists.
- Check that required subdirectories (plans, runs, templates, prompts, hooks) exist under each root.
- Validate `default_project` matches a key in `roots` (leveraging validation from TASK-013).
- Report missing template, prompt, or hook files under configured root(s) — same checks as today but against the correct paths.
- Use parameterized `required_paths(artifact_root)` from scaffold.py.

# Out of scope

- Config key validation logic (TASK-013 — already done).
- Scaffolding missing directories (that's `onward init`).
- Multi-root sync validation (TASK-027).

# Files to inspect

- `src/onward/cli_commands.py` — `cmd_doctor` function
- `src/onward/scaffold.py` — `required_paths`
- `src/onward/config.py` — `validate_config_contract_issues`

# Implementation notes

- Doctor currently checks `.onward/` paths. Replace each hardcoded path with layout-derived paths.
- When multiple roots are configured, doctor should check each one and label findings with the project key.
- Missing directories should be warnings, not errors — the user can run `onward init` to fix.
- Keep the existing doctor output format (pass/warn/fail) so users see familiar output.

# Acceptance criteria

- `onward doctor` with `root: nb` reports missing `nb/plans/` if it doesn't exist.
- `onward doctor` with valid `roots` config and all directories present shows all-pass.
- `onward doctor` with `roots: {a: .a, b: .b}` checks both `.a/` and `.b/` trees.
- No hardcoded `.onward/` path checks remain in cmd_doctor (except for config file location).

# Handoff notes

- Run `onward doctor` in the onward repo itself to verify backward compatibility (default `.onward` root).
