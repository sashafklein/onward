---
id: PLAN-003
type: plan
title: Decomposition engine for plan and chunk splitting
status: open
description: Turn high-level scope into executable artifacts with bounded AI assistance
priority: medium
model: gpt-5
created_at: 2026-03-19T00:00:00Z
updated_at: 2026-03-19T00:00:00Z
---

# Summary

Implement `split` commands that transform a plan into chunks and a chunk into tasks.

# Problem

Manual decomposition is slow and inconsistent for AI-heavy implementation loops.

# Goals

- Implement `train split PLAN-###` and `train split CHUNK-###`.
- Produce artifacts with clean acceptance criteria and model defaults.
- Keep deterministic file output even when model responses vary.

# Non-goals

- Full autonomous execution of generated tasks.
- Background scheduling.

# Context

Unlike `new`, `split` is explicitly generative and is allowed to invoke models by default.

# Proposed approach

Define a split prompt contract plus output parser that validates and normalizes generated chunks/tasks before writing files.

# Risks

- Model output format drift causing parse failures.
- Overly broad tasks that break execution flow.

# Chunking strategy

1. Prompt + response schema for split output.
2. Normalization and validation layer.
3. Safe file write and dry-run mode.

# Acceptance criteria

- `train split PLAN-###` creates one or more valid `CHUNK-*` artifacts.
- `train split CHUNK-###` creates one or more valid `TASK-*` artifacts.
- Generated tasks include acceptance criteria and model metadata.
- A `--dry-run` mode prints planned artifacts without writing them.
- Invalid generated output fails with actionable parse diagnostics.

# Notes

Keep split prompts local and versioned under `.train/prompts/` when introduced.
