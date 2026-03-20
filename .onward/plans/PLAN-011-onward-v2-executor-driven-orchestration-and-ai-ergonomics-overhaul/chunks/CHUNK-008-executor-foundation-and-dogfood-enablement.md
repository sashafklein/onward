---
id: "CHUNK-008"
type: "chunk"
plan: "PLAN-011"
project: ""
title: "Executor foundation and dogfood enablement"
status: "open"
description: "Replace ralph coupling with generic executor, create reference executor script, add plan-level work, add default commit hook. This unblocks dogfooding all subsequent chunks."
priority: "high"
model: "opus-latest"
estimated_files: 25
depends_on: []
created_at: "2026-03-20T15:52:20Z"
updated_at: "2026-03-20T15:52:20Z"
---

# Summary

Replace the hardcoded "ralph" executor coupling with a configurable `executor` abstraction, create a reference executor script that routes to cursor/claude-code based on model, add `onward work PLAN-*` support, and wire in a default commit-after-task hook. After this chunk lands, Onward can execute real work and dogfood itself.

# Scope

- Rename `ralph.*` config to `executor.*` (backward-compatible alias for `ralph`)
- Replace all "ralph" references in source, tests, error messages, docs
- Create `scripts/onward-exec` reference executor script
- Add `onward work PLAN-*` that drains chunks in order
- Add default `post_task_shell` commit hook in scaffold
- Update AGENTS.md, INSTALLATION.md, WORK_HANDOFF.md, LIFECYCLE.md

# Out of scope

- Parallel execution (sequential only in this chunk)
- Intelligent split (chunk 3)
- Status model changes (chunk 2)
- Structured feedback beyond exit code + basic ack (chunk 4)

# Dependencies

None. This is the first chunk.

# Expected files/systems involved

- `src/onward/config.py` — executor config loading, remove model resolution
- `src/onward/execution.py` — replace ralph references, add plan-level work
- `src/onward/cli.py` — parser updates
- `src/onward/cli_commands.py` — plan-level work handler
- `src/onward/scaffold.py` — new default config shape, commit hook
- `src/onward/preflight.py` — rename ralph preflight
- `scripts/onward-exec` — new reference executor script
- `docs/WORK_HANDOFF.md`, `docs/LIFECYCLE.md`, `INSTALLATION.md`, `AGENTS.md`
- `tests/test_cli_work.py`, `tests/test_cli_review.py`, `tests/test_preflight.py`, `tests/test_architecture_seams.py`

# Completion criteria

- [ ] `onward init` creates config with `executor:` key (not `ralph:`)
- [ ] `onward work TASK-X` invokes the configured executor command
- [ ] `onward work CHUNK-X` drains tasks and auto-completes chunk
- [ ] `onward work PLAN-X` drains chunks and auto-completes plan
- [ ] `scripts/onward-exec` exists and can route to claude CLI
- [ ] Default post-task hook commits with task ID in message
- [ ] All existing tests pass with updated config shape
- [ ] `onward doctor` validates executor config
- [ ] Docs updated: no "ralph" references except in migration notes

# Notes

The executor script is intentionally a thin routing layer. It reads the model from the JSON payload, picks the appropriate CLI tool (claude for Claude models, cursor for others), formats the context as a prompt, and captures output. The intelligence lives in the AI model, not the script.
