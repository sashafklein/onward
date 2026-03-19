---
id: PLAN-002
type: plan
title: Visibility surfaces and artifact state transitions
status: open
description: Implement momentum-oriented views and deterministic status mutation
priority: high
model: gpt-5
created_at: 2026-03-19T00:00:00Z
updated_at: 2026-03-19T00:00:00Z
---

# Summary

Add the status transition commands and visibility views that make Trains operational day to day.

# Problem

Artifacts exist, but there is no reliable way to see what is active, finished, or next.

# Goals

- Implement `start`, `complete`, `cancel`, and `archive`.
- Provide `progress`, `recent`, and `next` views.
- Regenerate derived indexes from artifact files.

# Non-goals

- Model-based splitting.
- Executor integration.

# Context

The state model stays simple (`open`, `in_progress`, `completed`, `canceled`), with blocking represented via metadata.

# Proposed approach

Use a small status transition engine with common timestamp/update behavior shared by all artifact types.

# Risks

- Drift between artifact files and derived indexes.
- Illegal state transitions if command guards are weak.

# Chunking strategy

1. Transition rules and mutation helpers.
2. Index regeneration pipeline.
3. Visibility commands and sorting heuristics.

# Acceptance criteria

- `train start|complete|cancel <ID>` updates status and `updated_at` deterministically.
- `train archive PLAN-###` moves the plan directory into `.train/plans/.archive/` and removes it from active index.
- `train progress` shows all `in_progress` artifacts and active runs.
- `train recent` shows recently completed artifacts in reverse chronological order.
- `train next` picks open tasks with no unmet dependencies before higher-level work.

# Notes

This plan should land before decomposition and work execution.
