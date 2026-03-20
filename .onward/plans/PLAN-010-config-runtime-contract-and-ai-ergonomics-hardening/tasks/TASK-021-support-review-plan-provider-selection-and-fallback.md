---
id: "TASK-021"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-007"
project: ""
title: "Support review-plan provider selection and fallback"
status: "open"
description: "Allow reviewer matrix across multiple providers with clear config"
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

PLAN-010 problem + acceptance: **`review-plan`** needs explicit **multi-provider / model matrix** (OpenClaw-oriented path, plus Claude CLI + Cursor agent CLI options documented and tested).

# Scope

- Config + CLI for reviewer selection and ordered fallback when a provider/model is unavailable.
- Deterministic logging when falling back (plan §5b).

# Out of scope

- Full OpenClaw server implementation; TASK-019 preflight (coordinate).

# Files to inspect

- `src/onward/cli.py` (`cmd_review_plan` / related), `execution.py`, `config.py`, `scaffold.py`, README/INSTALLATION

# Implementation notes

- Maintain single-provider default path per plan risk section.

# Acceptance criteria

- At least one matrix configuration works in tests or dogfood; docs describe how to set reviewers and fallbacks.

# Handoff notes

<!-- Fill when closing. -->
