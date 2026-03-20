---
id: "TASK-023"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-006"
project: ""
title: "Initialize dogfood workspace deterministically"
status: "open"
description: "Ensure fixture includes required gitignore/workspace init state or docs mandate init step"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:52Z"
updated_at: "2026-03-20T00:28:52Z"
---

# Context

PLAN-010 acceptance **dogfood reliability**: fresh dogfood run must not need **undocumented manual `init`** reconciliation — bootstrap should leave a valid Onward workspace every time.

# Scope

- Ensure dogfood scripts run `onward init` (or equivalent) in the consumer workspace with deterministic config.
- Align `.dogfood/consumer-app` fixture with what scripts expect.

# Out of scope

- Rewriting consumer app business logic.

# Files to inspect

- `scripts/dogfood/bootstrap.sh`, `scripts/dogfood/e2e.sh`, `.dogfood/consumer-app/`, `docs/DOGFOOD.md`

# Implementation notes

- Idempotent: safe to run twice without manual cleanup.

# Acceptance criteria

- CI or local doc’d procedure: clone → bootstrap → e2e passes with no extra init steps.

# Handoff notes

<!-- Fill when closing. -->
