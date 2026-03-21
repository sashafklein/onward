---
id: "TASK-040"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-010"
project: ""
title: "Add split output validation and sizing checks"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on:
  - "TASK-038"
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:04Z"
updated_at: "2026-03-20T18:17:36Z"
---

# Context

After TASK-038 wires split to the executor and TASK-039 improves the prompts, this task adds validation on the executor's JSON output. AI-generated split output can have issues: too many files per task, missing fields, dependency cycles, oversized chunks. This task catches these problems before artifacts are written to disk, with warnings in dry-run mode and errors in write mode.

# Scope

- Add `validate_split_output(items, split_type)` function in `split.py` that returns `(warnings: list[str], errors: list[str])`
- Validate chunk output:
  - Each chunk has `title` and `description` (already enforced by `normalize_chunk_candidates`)
  - Chunk count sanity: warn if < 2 or > 15 chunks
  - No dependency cycles in `depends_on` references
- Validate task output:
  - Each task has `title`, `description`, `acceptance` (already enforced)
  - File count per task: warn at 7-9 files, error at >9
  - Task count per chunk: warn if > 10 tasks
  - No dependency cycles in `depends_on`
  - Model field is a known alias or resolved name
- Integrate validation into `cmd_split`:
  - In dry-run mode: print warnings and errors, but don't fail (informational)
  - In write mode: print warnings, fail on errors (don't write files)
- Add `--force` flag to `onward split` that writes even when validation errors exist

# Out of scope

- Validating file paths exist on disk (files may not exist yet)
- Cross-chunk dependency validation (only intra-split validation)
- Re-running the executor if validation fails

# Files to inspect

- `src/onward/split.py` — add `validate_split_output()`, integrate with existing normalization
- `src/onward/cli.py` — split subparser, add `--force` flag
- `src/onward/cli_commands.py` — `cmd_split()` to call validation and handle results
- `tests/test_cli_split.py` — add validation test cases

# Implementation notes

- Dependency cycle detection: build a directed graph from `depends_on` indices/references, check for cycles with a simple DFS/topological sort. The items are small (typically <15), so algorithmic efficiency doesn't matter.
- File count validation: read the `files` list from each task item. If `files` is absent or empty, skip the check (AI might not always emit file lists).
- The validation function should be independent of write logic — call it between normalization and `prepare_*_writes`.
- For the `--force` flag: when set, print errors as warnings and proceed. When not set, errors cause non-zero exit.
- Model validation: check against `MODEL_FAMILIES` keys and their `-latest` forms in `config.py`. Unknown models get a warning (not error), since users may have custom model strings.
- Consider: should validation also check that task titles are unique within a split? Yes — duplicate titles would create filename collisions.

# Acceptance criteria

- `onward split --dry-run` shows validation warnings/errors alongside planned artifacts
- `onward split` fails (non-zero exit) on validation errors without `--force`
- `onward split --force` writes files despite validation errors (with printed warnings)
- Tasks with >9 files produce a validation error
- Tasks with 7-9 files produce a warning
- Dependency cycles are detected and reported as errors
- Duplicate task titles within a split produce an error
- Tests cover: oversized tasks, dependency cycles, duplicate titles, force flag

# Handoff notes

- This completes the CHUNK-010 intelligent split trilogy (038 → 039 → 040).
- The validation is intentionally lenient with warnings — AI output is imperfect, and blocking on every issue would make split unusable. Errors are reserved for things that would break the system (cycles, collisions).
- Future enhancement: `--auto-fix` flag that re-runs the executor with validation feedback to fix issues.
