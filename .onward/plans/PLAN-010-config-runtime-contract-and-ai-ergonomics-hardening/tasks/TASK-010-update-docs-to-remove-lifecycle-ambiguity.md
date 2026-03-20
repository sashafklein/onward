---
id: "TASK-010"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-004"
project: ""
title: "Update docs to remove lifecycle ambiguity"
status: "completed"
description: "Synchronize README, INSTALLATION, CONTRIBUTION with actual state machine"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:22Z"
updated_at: "2026-03-20T00:55:49Z"
---

# Context

PLAN-010 acceptance: **README / INSTALLATION / CONTRIBUTION** show the **same** lifecycle rules and command expectations as `docs/LIFECYCLE.md` and TASK-009 behavior. Removes residual “strict start/complete every task” folklore.

# Scope

- Sweep README, INSTALLATION, CONTRIBUTION, optional SKILL examples, and any diagrams/quick-refs for contradictions.
- Add a short **capability truth table** (plan phase 2 §5): what is model-backed vs heuristic vs test-only.
- Cross-link `docs/LIFECYCLE.md` everywhere the loop is described.

# Out of scope

- Implementing new split/review behavior; changing CLI (TASK-009).

# Files to inspect

- `README.md`, `INSTALLATION.md`, `docs/CONTRIBUTION.md`, `docs/LIFECYCLE.md`, `.onward/templates/`, `docs/WORK_HANDOFF.md`

# Implementation notes

- Align “AI-assisted split/review” claims with actual default paths (heuristic fallback) per plan problem statement.

# Acceptance criteria

- No doc claims mandatory `complete` after successful `work` unless documenting an optional discipline choice clearly labeled as such.
- Truth table committed; spot-check commands in docs against `onward --help`.

# Handoff notes

- New **`docs/CAPABILITIES.md`** — truth table (executor vs heuristic vs `TRAIN_SPLIT_RESPONSE`).
- **README**: split rows corrected; “Moving Work Forward” + “Model vs local behavior” link LIFECYCLE/CAPABILITIES; docs table expanded.
- **INSTALLATION**: quick-ref + troubleshooting no longer claim “AI-decompose” for split.
- **CONTRIBUTION** §1 + §8 links: LIFECYCLE, CAPABILITIES.
- **WORK_HANDOFF**: link to CAPABILITIES.
- **LIFECYCLE**: removed stale TASK-010 follow-up; “Related docs” points to CAPABILITIES.
- **CLI**: `split` `--help` one-liner mentions heuristics + CAPABILITIES.
