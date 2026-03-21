---
id: "PLAN-007"
type: "plan"
project: ""
title: "Metadata validation and frontmatter cleanup"
status: "in_progress"
description: "Add strict metadata validation to onward work (pre-flight) and doctor, rename effort→complexity, remove dead frontmatter fields"
priority: "high"
model: "opus"
created_at: "2026-03-21T19:53:45Z"
updated_at: "2026-03-21T20:30:49Z"
---

# Summary

Harden artifact metadata by adding validation that catches bad values early (before
`onward work` marks a task in_progress), remove frontmatter fields that duplicate
body content without being consumed by anything, and rename `effort` to `complexity`
since the field drives model selection (intellectual difficulty), not labor/time.

# Problem

1. **No metadata validation on `work`.** If a task has `effort: banana` or `model: gpt-7`,
   nothing catches it until the executor fails — after the task is already `in_progress`
   with a run record started. The user must manually clean up.

2. **`validate_artifact` is shallow.** It checks that required fields exist and that
   `status` is valid, but ignores value constraints on `effort`, `priority`, `model`,
   `human`, and unknown/extra fields entirely. `doctor` inherits this gap.

3. **`files` and `acceptance` in task frontmatter are dead weight.** Both are rendered
   into the markdown body during `split`, then the frontmatter copies are never read by
   the executor, prompt builder, or any validation. They're duplicated noise.

4. **`effort` is the wrong word.** The field maps to model tier (how smart the model
   needs to be). That's complexity/difficulty, not effort. A bulk rename across 50 files
   is high-effort but low-complexity; a tricky concurrency fix is the opposite.

5. **`effort` and `model` have a broken bridge.** `normalize_effort` accepts
   `xs|s|m|l|xl` but `resolve_model_for_task` only maps `high|medium|low` to tiers.
   T-shirt sizes silently fall through to the default.

# Goals

- Add a `validate_artifact_metadata()` function that checks value constraints for all
  typed fields (status, priority, effort/complexity, model, human, type references)
- Call it in `onward work` as a pre-flight gate BEFORE marking in_progress
- Integrate it into `onward doctor` for workspace-wide checks
- Rename `effort` → `complexity` everywhere (frontmatter key, CLI flags, config,
  code, docs, prompts, tests)
- Unify the vocabulary: `complexity` accepts `low | medium | high` and maps directly
  to model tiers (which already use these names)
- Remove `files` and `acceptance` from task frontmatter schema (keep them only in body)
- Optionally warn on unknown frontmatter fields (fields not in the known schema for
  that artifact type)

# Non-goals

- Not changing the model tier system itself (that's config.py, works fine)
- Not removing `model` from frontmatter — explicit model override remains valid
- Not changing how `acceptance` works in the ack schema (acceptance_met/unmet in
  executor results is fine; that reads from the body)
- Not blocking on PLAN-006 (model aliases) — orthogonal

# End state

- [ ] `onward work TASK-X` with `complexity: banana` → clear error, task stays `open`
- [ ] `onward work TASK-X` with `model: nonexistent` → clear error, task stays `open`
- [ ] `onward doctor` reports bad `complexity`, `priority`, `status`, `model` values
- [ ] `onward doctor` warns on unknown frontmatter fields
- [ ] All references to `effort` renamed to `complexity` across source, tests, docs
- [ ] `complexity` accepts `low | medium | high` only (no more t-shirt sizes)
- [ ] `files` and `acceptance` no longer emitted in task frontmatter by `split`/`new`
- [ ] Existing tasks with old `effort` key still work (migration/compat in validation)

# Context

Relevant code paths:
- `src/onward/artifacts.py`: `REQUIRED_FIELDS`, `validate_artifact()` — currently shallow
- `src/onward/execution.py`: `_work_task()` at line ~1040 — status/dep checks but no metadata validation
- `src/onward/config.py`: `resolve_model_for_task()` — effort→tier mapping, `_EFFORT_TIER_VALUES`
- `src/onward/util.py`: `normalize_effort()` — accepts xs/s/m/l/xl
- `src/onward/split.py`: emits `files` and `acceptance` in frontmatter during split
- `src/onward/cli_commands.py`: `cmd_doctor()`, `new task`/`batch` commands

# Proposed approach

## Chunk 1: Metadata validation

1. Define `KNOWN_FIELDS` per artifact type in `artifacts.py` — the complete set of
   allowed frontmatter keys for plan, chunk, and task.
2. Define `FIELD_VALIDATORS` — a dict of field name → validation function. E.g.:
   - `status`: must be in `{open, in_progress, completed, canceled, failed}`
   - `priority`: must be in `{low, medium, high}`
   - `complexity`: must be in `{low, medium, high}` (with compat for old `effort` values)
   - `human`: must be boolean-ish
   - `model`: must be a non-empty string (optionally: warn if not a known alias or
     canonical model, but don't hard-fail since new models appear)
3. Expand `validate_artifact()` to call field validators and warn on unknown fields.
4. Add `validate_task_preflight()` in `execution.py` — called before `update_artifact_status`
   in `_work_task()`. On failure: raise with a clear message, task stays `open`.
5. Update `cmd_doctor` to surface the richer validation.

## Chunk 2: Rename effort → complexity

1. `util.py`: rename `normalize_effort` → `normalize_complexity`, accept `low|medium|high`.
2. `config.py`: rename `_EFFORT_TIER_VALUES`, update `resolve_model_for_task` to read
   `complexity` key (with fallback to `effort` for compat).
3. `split.py`: emit `complexity` instead of `effort` in generated frontmatter.
4. `cli_commands.py`: rename `--effort` flag → `--complexity` on `new task`, `batch`.
5. `artifacts.py`: add `complexity` to known fields, treat `effort` as deprecated alias.
6. Update all prompts, templates, and docs.
7. Update tests.

## Chunk 3: Remove dead frontmatter fields

1. `split.py`: stop emitting `files` and `acceptance` in task frontmatter metadata dict.
   They're already rendered into the body — that's sufficient.
2. `cli_commands.py` (`cmd_batch`): same — stop putting `files`/`acceptance` in metadata.
3. `artifacts.py`: do NOT include `files`/`acceptance` in `KNOWN_FIELDS` for tasks.
   Existing tasks with these fields will get an "unknown field" warning from doctor,
   which is the desired nudge to clean up.
4. Update tests that assert on frontmatter content.

# Acceptance criteria

- `validate_artifact()` catches: bad status, bad priority, bad complexity, unknown fields
- `onward work` calls validation pre-flight; bad metadata → error + task stays open
- `onward doctor` reports all metadata issues found across the workspace
- Zero references to `effort` remain in source (except compat fallback in config.py)
- `normalize_complexity("low"|"medium"|"high")` works; anything else returns `""`
- Task frontmatter from `split`/`new task`/`batch` no longer includes `files`/`acceptance`
- All existing tests pass (updated as needed)
- New tests cover: validation logic, pre-flight gate in work, complexity normalization

# Notes

- Backward compat: existing tasks with `effort: s` should get a doctor warning but not
  hard-fail `work` — treat unrecognized complexity as "default tier" with a warning.
  Over time, users clean them up.
- The `model` field is NOT removed. `complexity` drives the default model; `model`
  overrides it. Both can coexist, but `model` takes precedence (existing behavior).
