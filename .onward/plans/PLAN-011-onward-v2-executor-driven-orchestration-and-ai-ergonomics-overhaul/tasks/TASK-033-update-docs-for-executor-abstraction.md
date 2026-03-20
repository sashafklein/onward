---
id: "TASK-033"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-008"
project: ""
title: "Update docs for executor abstraction"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on:
  - "TASK-029"
  - "TASK-030"
  - "TASK-031"
  - "TASK-032"
blocked_by: []
files:
  - "AGENTS.md"
  - "INSTALLATION.md"
  - "README.md"
  - "docs/WORK_HANDOFF.md"
  - "docs/LIFECYCLE.md"
  - "docs/CAPABILITIES.md"
  - "docs/AI_OPERATOR.md"
acceptance:
  - "grep -r 'ralph' docs/ AGENTS.md INSTALLATION.md README.md returns zero hits outside migration notes"
  - "all doc references to config use executor not legacy ralph key"
  - "LIFECYCLE.md documents plan-level work"
created_at: "2026-03-20T16:00:56Z"
updated_at: "2026-03-20T16:47:31Z"
---

# Context

This is the final task in CHUNK-008. All code changes are complete: the ralph→executor rename (TASK-029), the reference executor script (TASK-030), plan-level work (TASK-031), and the default commit hook (TASK-032). This task updates every documentation file to reflect the new reality. The docs must be the source of truth for users and AI operators.

# Scope

- **AGENTS.md**: Update codebase notes section to mention `executor` instead of `ralph`. Update the command loop example if it references executor config. Ensure the "Source lives in `src/onward/`" section mentions `preflight.py` and `executor_ack.py` accurately.
- **INSTALLATION.md**: Update the config reference section. Replace `ralph:` config examples with `executor:` examples. Update the first-run walkthrough to mention `executor.command: onward-exec`. Add a migration note: "If your config uses `ralph:`, it still works but will show a deprecation warning on `onward doctor`."
- **README.md**: Update any config examples from `ralph:` to `executor:`. Update the executor description. If there's a quickstart section, ensure it shows the new config shape.
- **docs/WORK_HANDOFF.md**: Update the executor bridge section to describe the `scripts/onward-exec` script. Update hook documentation to mention `ONWARD_TASK_ID`, `ONWARD_TASK_TITLE`, `ONWARD_RUN_ID` env vars. Update any `ralph` references. Document the default `post_task_shell` commit hook.
- **docs/LIFECYCLE.md**: Add a section on plan-level work (`onward work PLAN-*`). Describe the execution order: plan → chunks (sorted by ID) → tasks (sorted by ID, respecting depends_on). Document that failed chunks stop plan execution and the plan remains `in_progress`.
- **docs/CAPABILITIES.md**: Update the capability matrix if it lists executor/ralph features. Ensure plan-level work is listed as a capability.
- **docs/AI_OPERATOR.md**: Update the quickstart to use `executor` config key. Update any operator instructions that reference `ralph`. Ensure the getting-started flow mentions `scripts/onward-exec`.

# Out of scope

- Writing new documentation pages (only updating existing ones)
- Updating schema files (those are code artifacts, not docs)
- Updating `.onward/prompts/` or `.onward/hooks/` templates (those were handled in TASK-029)
- Writing a migration guide (a one-line note in INSTALLATION.md is sufficient for now)
- Changelog or release notes (future task)

# Files to inspect

- `AGENTS.md` — search for `ralph`, `executor`, config examples
- `INSTALLATION.md` — search for `ralph`, config reference sections
- `README.md` — search for `ralph`, config examples, quickstart
- `docs/WORK_HANDOFF.md` — executor bridge, hooks, env vars
- `docs/LIFECYCLE.md` — status transitions, work command documentation
- `docs/CAPABILITIES.md` — feature matrix
- `docs/AI_OPERATOR.md` — operator quickstart, config instructions

# Implementation notes

- **Search-and-replace is not enough**: Don't blindly replace "ralph" with "executor" — some occurrences may be in different contexts (e.g., "ralph" as a proper noun in commit history references, or in the backward-compat migration note). Read each file and make thoughtful updates.
- **Config examples**: Every YAML config example should show the `executor:` shape:
  ```yaml
  executor:
    command: onward-exec
    args: []
    enabled: true
  ```
- **Migration note template**: Add a brief note wherever the config is documented:
  > **Migration**: If your config uses the `ralph:` key, it continues to work. Rename it to `executor:` to silence the deprecation warning from `onward doctor`.
- **Plan-level work in LIFECYCLE.md**: Add after the existing chunk-level work section. Keep it concise:
  - `onward work PLAN-*` sets the plan to `in_progress`
  - Drains chunks in ID order (skipping completed/canceled)
  - Each chunk drains its tasks (same as `onward work CHUNK-*`)
  - If a chunk fails, plan execution stops; plan stays `in_progress`
  - After all chunks complete, plan is auto-completed
- **Env vars documentation**: In WORK_HANDOFF.md, add a section listing environment variables available to hooks and the executor:
  - `ONWARD_RUN_ID` — unique run identifier
  - `ONWARD_TASK_ID` — the task being executed
  - `ONWARD_TASK_TITLE` — human-readable task title
- **Default commit hook documentation**: In WORK_HANDOFF.md, document the default `post_task_shell` hook, what it does, and how to disable it (`post_task_shell: []`).
- **Consistency check**: After all updates, run `rg ralph` across the doc files to confirm zero hits outside intentional migration notes.

# Acceptance criteria

- `rg ralph AGENTS.md INSTALLATION.md README.md docs/` returns zero matches outside explicit migration/backward-compat notes
- All YAML config examples in docs show `executor:` not `ralph:`
- `docs/LIFECYCLE.md` has a section describing `onward work PLAN-*` behavior
- `docs/WORK_HANDOFF.md` documents the env vars (`ONWARD_TASK_ID`, `ONWARD_TASK_TITLE`, `ONWARD_RUN_ID`) and the default commit hook
- `INSTALLATION.md` has a migration note about the ralph→executor rename
- `docs/AI_OPERATOR.md` references `executor` config and `scripts/onward-exec`
- No broken markdown links in updated files

# Handoff notes

After this task, CHUNK-008 is complete. The entire executor foundation is in place: renamed config, reference script, plan-level work, commit hooks, and accurate docs. Run `onward doctor` on the workspace to verify the config is clean. The next chunk can build on this foundation knowing the docs are trustworthy.
