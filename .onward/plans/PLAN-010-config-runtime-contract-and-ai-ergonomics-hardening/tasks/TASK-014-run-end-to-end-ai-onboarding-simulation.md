---
id: "TASK-014"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-006"
project: ""
title: "Run end-to-end AI onboarding simulation"
status: "completed"
description: "Fresh workspace bootstrap and agent behavior validation against instructions"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:22Z"
updated_at: "2026-03-20T01:14:14Z"
---

# Context

PLAN-010 phase 4 §8 + acceptance **AI onboarding proof**: fresh workspace using **install instructions only** + documented agent block; run full loop without undocumented recovery.

# Scope

- Script or documented procedure: `init` → `new plan/chunk/task` → `report` / `next` → `work` (or equivalent per LIFECYCLE) → `report`.
- Verify artifacts, statuses, indexes, run records.
- Include **dogfood** checks: Python version in venv, `onward` on PATH, deterministic bootstrap (`scripts/dogfood/*`).

# Out of scope

- Multi-provider review matrix (TASK-021); execution proof schema (TASK-020) — stub or mock executor if needed.

# Files to inspect

- `INSTALLATION.md`, `scripts/dogfood/bootstrap.sh`, `scripts/dogfood/e2e.sh`, `docs/DOGFOOD.md`, `tests/`, `.dogfood/`

# Implementation notes

- Prefer CI-runnable smoke (may use `true` as executor like existing tests). Record gaps as new tasks.

# Acceptance criteria

- Reproducible E2E doc or automated test; no hidden manual `init` reconciliation for dogfood (aligns TASK-023).

# Handoff notes

- Added CI-runnable `tests/test_onboarding_simulation.py`: `init` → `doctor` → `new plan/chunk/task` → `next` → `report` → `work TASK-001` with executor `true`; asserts task frontmatter, run JSON, and `index.yaml` contains TASK-001 as completed (regex on index — full YAML is list-of-maps beyond `parse_simple_yaml`).
- Linked from `docs/CONTRIBUTION.md` automated test list.
- Dogfood shell e2e (`scripts/dogfood/e2e.sh`) unchanged; still the install/venv path — pytest test covers the documented CLI loop without venv.
