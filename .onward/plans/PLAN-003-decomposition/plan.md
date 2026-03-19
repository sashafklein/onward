---
id: "PLAN-003"
type: "plan"
title: "Decomposition engine for plan and chunk splitting"
status: "in_progress"
description: "Turn high-level scope into executable artifacts with bounded AI assistance"
priority: "medium"
model: "gpt-5"
created_at: "2026-03-19T00:00:00Z"
updated_at: "2026-03-19T04:35:34Z"
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

Current pickup point:

1. Add `train split PLAN-###` and `train split CHUNK-###` commands.
2. Introduce prompt assets under `.train/prompts/` with deterministic parse format.
3. Implement `--dry-run` and validation errors that do not write partial artifacts.

## Detailed continuation plan

### Phase 1: CLI surface + command contract

1. Add top-level `split` parser with:
   - `train split PLAN-### [--dry-run] [--model MODEL]`
   - `train split CHUNK-### [--dry-run] [--model MODEL]`
2. Resolve target artifact by ID and hard-fail on type mismatch.
3. Choose model in this order: `--model`, config `models.split_default`, fallback `gpt-5`.

### Phase 2: Prompt assets + deterministic response format

1. Add prompt templates under `.train/prompts/`:
   - `split-plan.md` (plan -> chunk candidates)
   - `split-chunk.md` (chunk -> task candidates)
2. Require strict JSON output with explicit schema fields.
3. Include source artifact metadata and body in prompt context.

### Phase 3: Normalization + validation

1. Parse model output into typed in-memory candidates.
2. Validate required fields before any write:
   - chunk: `title`, `description`
   - task: `title`, `description`, `acceptance`, `model`
3. Normalize:
   - trim whitespace
   - drop empty list items
   - clamp priority/model defaults to allowed values
4. Emit actionable diagnostics that point to the first invalid item and field.

### Phase 4: Write path + dry-run safety

1. Build all destination file paths and frontmatter in memory first.
2. If any validation or path collision fails, write nothing.
3. `--dry-run` prints planned artifacts and target paths only.
4. Normal mode writes all artifacts then refreshes indexes once.

### Phase 5: Tests

1. Parser tests for valid/invalid split payloads.
2. CLI tests:
   - `split PLAN-### --dry-run` creates no files.
   - `split CHUNK-###` writes valid tasks with acceptance criteria.
   - invalid payload returns non-zero and leaves filesystem unchanged.
3. Regression test for deterministic file naming and ID assignment order.

### Exit criteria for PLAN-003

1. `split` command exists in `train --help` and routes correctly by ID type.
2. Prompts are file-backed and loaded from `.train/prompts/`.
3. Generated artifacts are validated and atomic on write.
4. `--dry-run` is fully non-mutating.
5. Automated tests cover success path and parse/validation failures.
