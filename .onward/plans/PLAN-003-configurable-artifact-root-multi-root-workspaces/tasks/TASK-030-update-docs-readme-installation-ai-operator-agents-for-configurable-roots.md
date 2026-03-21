---
id: "TASK-030"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-008"
project: ""
title: "Update docs (README, INSTALLATION, AI_OPERATOR, AGENTS) for configurable roots"
status: "open"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "m"
depends_on: []
files: []
acceptance: []
created_at: "2026-03-21T15:50:00Z"
updated_at: "2026-03-21T15:50:00Z"
---

# Context

User-facing documentation currently references `.onward/` as the sole artifact directory. With configurable roots, docs must explain the new `root` and `roots` config options and stop implying `.onward/` is the only possibility.

# Scope

- **README.md**: Update the configuration section to document `root`, `roots`, and `default_project` keys. Add a "Multi-root workspaces" subsection explaining when and how to use multiple roots. Update any `.onward/` path references to say "artifact root" or "configured root".
- **docs/INSTALLATION.md**: Update the config reference table to include `root`, `roots`, `default_project`. Show example configs for single custom root and multi-root.
- **docs/AI_OPERATOR.md**: Update path references so AI agents know to check the configured root, not assume `.onward/`. Mention `--project` flag.
- **AGENTS.md**: Update the Onward codebase notes to mention configurable roots and the `--project` flag.

# Out of scope

- Changing code behavior (all code changes are in other tasks).
- Updating LIFECYCLE.md or CAPABILITIES.md (unless they reference `.onward/` paths).
- Writing a migration guide (future work if needed).

# Files to inspect

- `README.md`
- `docs/INSTALLATION.md`
- `docs/AI_OPERATOR.md`
- `AGENTS.md`

# Implementation notes

- Use "artifact root" as the generic term for the directory (whether `.onward`, `nb`, or a custom path).
- Don't remove all `.onward/` references — it's still the default. Just make it clear it's configurable.
- Example config snippets to include:
  ```yaml
  # Single custom root
  root: notebooks
  
  # Multi-root
  roots:
    frontend: .fe-plans
    backend: .be-plans
  default_project: frontend
  ```
- Mention that `--project` is required for multi-root commands unless `default_project` is set.
- Check LIFECYCLE.md and CAPABILITIES.md for any `.onward/` references that need updating.

# Acceptance criteria

- No doc claims `.onward/` is the only possible artifact location.
- `root`, `roots`, `default_project` are documented in INSTALLATION.md config reference.
- README has a "Multi-root workspaces" section.
- AI_OPERATOR.md mentions checking the configured root.
- AGENTS.md references `--project` flag.

# Handoff notes

- This can be done in parallel with code tasks since it's documentation-only.
- Review the docs as a new user would — does the multi-root concept make sense on first read?
