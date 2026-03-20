---
id: "TASK-022"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-006"
project: ""
title: "Fix dogfood venv/runtime version parity"
status: "open"
description: "Ensure dogfood uses supported Python and generated entrypoint is executable on target shells"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:51Z"
updated_at: "2026-03-20T00:28:51Z"
---

# Context

PLAN-010 problem + phase 4: **dogfood** stress — venv / **Python version** must match package requirement (3.11+) so `pytest` / editable install and `onward` entrypoint behave consistently.

# Scope

- Fix `scripts/dogfood/bootstrap.sh` (and docs) to create venv with supported Python (`python3.11` or `uv` pin).
- Verify `./scripts/test.sh` / e2e use that interpreter.

# Out of scope

- Supporting EOL Python versions; consumer app code changes.

# Files to inspect

- `scripts/dogfood/bootstrap.sh`, `scripts/dogfood/e2e.sh`, `scripts/test.sh`, `docs/DOGFOOD.md`, `pyproject.toml`

# Implementation notes

- Fail fast with clear message if no suitable `python3.11+` on PATH.

# Acceptance criteria

- Fresh dogfood bootstrap runs tests on 3.11+; documented in DOGFOOD.md.

# Handoff notes

<!-- Fill when closing. -->
