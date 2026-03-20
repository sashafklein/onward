---
id: "TASK-019"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-007"
project: ""
title: "Add credential and availability preflight for review/split/work"
status: "open"
description: "Detect missing provider keys/tools early and provide actionable errors"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:46Z"
updated_at: "2026-03-20T00:28:46Z"
---

# Context

PLAN-010 **§5c**: **preflight** before expensive model work — verify required CLIs, env vars, and provider availability; actionable errors; optional degraded mode.

# Scope

- Hook before `review-plan`, `split` (when model-backed), `work` / markdown hooks: check binary on PATH, key env vars per provider (design with TASK-018).
- Return clear messages: missing binary, auth, unsupported model/provider pair.

# Out of scope

- Long-running health daemons; network calls to provider APIs unless trivial and documented.

# Files to inspect

- `src/onward/cli.py`, `execution.py`, `split.py`, `config.py`, tests

# Implementation notes

- Must not break offline tests — mock or skip when `ralph.command` is `true`.

# Acceptance criteria

- Tests for failure modes; docs mention preflight behavior.

# Handoff notes

<!-- Fill when closing. -->
