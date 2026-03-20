---
id: "TASK-016"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-006"
project: ""
title: "Publish AI operator quickstart and anti-patterns"
status: "open"
description: "Document common failure modes and exact recovery playbooks"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:23Z"
updated_at: "2026-03-20T00:22:23Z"
---

# Context

PLAN-010 goal: agents operate from **docs alone**. A dedicated **operator quickstart** + **anti-patterns** doc reduces folklore (wrong lifecycle, skipping `work`, planning in chat).

# Scope

- New doc (e.g. `docs/AI_OPERATOR.md`) or README section: minimal loop, project flags, when to use `work` vs `complete`, sync basics, `human` / `blocked_by`.
- Anti-patterns: ad-hoc todos, ignoring `doctor`, assuming `split` is always model-backed, etc.

# Out of scope

- INSTALLATION agent paste block rewrite (TASK-010 may overlap — dedupe).

# Files to inspect

- `INSTALLATION.md`, `AGENTS.md`, `docs/LIFECYCLE.md`, `docs/WORK_HANDOFF.md`, `README.md`

# Implementation notes

- Link from README “Agent Integration” and INSTALLATION.

# Acceptance criteria

- Doc merged; links from README or INSTALLATION; consistent with LIFECYCLE.

# Handoff notes

<!-- Fill when closing. -->
