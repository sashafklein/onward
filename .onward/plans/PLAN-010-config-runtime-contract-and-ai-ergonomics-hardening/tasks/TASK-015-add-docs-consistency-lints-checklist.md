---
id: "TASK-015"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-006"
project: ""
title: "Add docs consistency lints/checklist"
status: "open"
description: "Catch drift between docs, defaults, and runtime in CI"
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

PLAN-010 phase 4 §9: **CI-visible drift checks** — stale doc command lists, template vs code, schema mismatches should fail PRs.

# Scope

- Lightweight scripts or pytest: e.g. extract `onward` subcommands from `--help` vs README/INSTALLATION mentions; diff scaffold keys vs config allowlist (overlap TASK-013).
- Contributor **checklist** in CONTRIBUTION for manual release steps if needed.

# Out of scope

- Full markdown linter for prose quality; spellcheck.

# Files to inspect

- `README.md`, `INSTALLATION.md`, `docs/CONTRIBUTION.md`, `pyproject.toml` / CI config, `tests/`

# Implementation notes

- Start with highest-value automated check; checklist documents the rest.

# Acceptance criteria

- At least one automated check merged; checklist committed; documented how to run locally.

# Handoff notes

<!-- Fill when closing. -->
