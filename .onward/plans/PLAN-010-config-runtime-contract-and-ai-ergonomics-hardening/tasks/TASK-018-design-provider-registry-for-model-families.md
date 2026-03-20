---
id: "TASK-018"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-007"
project: ""
title: "Design provider registry for model families"
status: "completed"
description: "Route models across OpenClaw, Claude CLI, Cursor agent CLI with explicit provider mapping"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:28:46Z"
updated_at: "2026-03-20T05:30:24Z"
---

# Context

PLAN-010 phase 2.5 **§5b**: explicit **provider routing** — map model families/aliases to concrete backends (OpenClaw, Claude CLI, Cursor agent CLI, etc.). Plan acceptance: review-plan matrix + documented paths.

# Scope

- Design config shape: e.g. `providers`, `models.*` routing tables, per-command overrides (`split`, `review-plan`, `work`, hooks).
- Document resolution order (task model → flag → config defaults).
- Optional feature flag for staged rollout (“Integration risk” in plan).

# Out of scope

- Implementing every provider adapter end-to-end (TASK-019/021); execution proof (TASK-020).

# Files to inspect

- `src/onward/execution.py` (`_model_alias`), `config.py`, `split.py`, review-plan path in `cli.py` / `execution.py`, `.onward.config.yaml` scaffold

# Implementation notes

- Keep default single-provider path unchanged until config opts in.

# Acceptance criteria

- Written design in `docs/` or plan chunk notes + ADR-style section; reviewed against acceptance “provider interoperability” bullets.

# Handoff notes

- Added **`docs/PROVIDER_REGISTRY.md`** — opt-in `provider_registry.enabled`, proposed `providers` / `models.routing` / per-command defaults, resolution order (artifact → routing → alias → defaults), doctor/contract notes, explicit non-goals.
- Linked from **README** (Documentation table), **docs/CAPABILITIES.md** (future section), **docs/CONTRIBUTION.md** §8.
