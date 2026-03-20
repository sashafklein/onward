---
id: "TASK-013"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-005"
project: ""
title: "Add architecture tests for module seams"
status: "open"
description: "Prevent boundary regressions with focused unit tests"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:22Z"
updated_at: "2026-03-20T00:22:22Z"
---

# Context

PLAN-010 phase 3 §7 + acceptance: **contract / architecture guardrails** — block reintroduction of config drift, forbidden imports, stale commands in docs, etc.

# Scope

- Add tests: e.g. scaffold template keys vs `CONFIG_*` allowlists; `cli.py` import rules; optional AST grep for private imports.
- Persisted format smoke checks where not already covered.
- Payload/schema validation hooks if missing.

# Out of scope

- Full static type enforcement of entire codebase; runtime performance tests.

# Files to inspect

- `tests/`, `src/onward/config.py`, `src/onward/scaffold.py`, `docs/schemas/`, TASK-004 handoff suggestions

# Implementation notes

- Keep tests fast and deterministic; run in default `pytest` CI.

# Acceptance criteria

- New tests fail on intentional drift fixtures; documented in CONTRIBUTION how to extend checks.

# Handoff notes

<!-- Fill when closing. -->
