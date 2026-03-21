---
id: "TASK-066"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-018"
project: ""
title: "Update PROVIDER_REGISTRY, CAPABILITIES, and LIFECYCLE docs"
status: "completed"
description: "Update documentation to reflect the new executor architecture, tiered model config, and batch execution semantics."
human: false
model: "composer-2"
effort: "medium"
depends_on: []
files:
- "docs/PROVIDER_REGISTRY.md"
- "docs/CAPABILITIES.md"
- "docs/LIFECYCLE.md"
- "AGENTS.md"
acceptance:
- "PROVIDER_REGISTRY.md reflects executor protocol (or archived with pointer)"
- "CAPABILITIES.md documents built-in executor and batch execution"
- "LIFECYCLE.md describes batch chunk/plan execution"
- "AGENTS.md references tiered model config"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-21T00:02:11Z"
run_count: 1
last_run_status: "completed"
---

# Context

All the functional work is done in earlier chunks. This task ensures documentation reflects the new reality.

# Scope

- `PROVIDER_REGISTRY.md`: Either rewrite to describe the Executor protocol and BuiltinExecutor/SubprocessExecutor, or archive the old design and point to the new code. The provider registry design was never implemented; the executor protocol supersedes it.
- `CAPABILITIES.md`: Add built-in executor to the executor-backed table. Document batch execution semantics. Update model resolution description.
- `LIFECYCLE.md`: Update `onward work CHUNK-*` section to describe batch execution. Note that all ready tasks are collected upfront and executed sequentially.
- `AGENTS.md`: Update model config references if any.

# Out of scope

- Code changes
- New documentation files

# Files to inspect

- `docs/PROVIDER_REGISTRY.md` -- current design doc to update
- `docs/CAPABILITIES.md` -- current capability table
- `docs/LIFECYCLE.md` -- current lifecycle description

# Acceptance criteria

- [ ] No documentation references the old flat model keys without noting they're deprecated
- [ ] Built-in executor is documented as the default
- [ ] Batch execution semantics are clear in LIFECYCLE.md
- [ ] PROVIDER_REGISTRY.md is updated or archived
