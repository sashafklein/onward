---
id: PLAN-001
type: plan
title: Core artifact engine and CLI foundations
status: open
description: Build deterministic file-based artifact creation, lookup, and validation
priority: high
model: gpt-5
created_at: 2026-03-19T00:00:00Z
updated_at: 2026-03-19T00:00:00Z
---

# Summary

Implement the minimum artifact engine for plans, chunks, and tasks.

# Problem

Without a deterministic artifact layer, every higher-level command becomes brittle.

# Goals

- Support `init`, `new`, `list`, and `show` for core artifact types.
- Enforce frontmatter presence and required fields.
- Keep IDs globally unique and easy to resolve.

# Non-goals

- Model execution.
- Sync and remote coordination.

# Context

The product is markdown-first and git-native; artifact files are source of truth.

# Proposed approach

Create a storage layer around `.train/plans/` that handles ID generation, file naming, and frontmatter parsing.

# Risks

- Inconsistent frontmatter parsing across edge cases.
- File naming collisions when titles are similar.

# Chunking strategy

1. Parser and schema validation.
2. ID generation + file path resolution.
3. Command wiring for create/list/show.

# Acceptance criteria

- `train new plan|chunk|task` creates valid markdown artifacts with required fields.
- `train list` returns all active artifacts in stable sort order.
- `train show <ID>` resolves and prints the correct artifact.
- Global IDs (`PLAN-*`, `CHUNK-*`, `TASK-*`) are unique and collision-safe.
- `train doctor` reports malformed frontmatter with actionable messages.

# Notes

This plan is the dependency base for all remaining plans.
