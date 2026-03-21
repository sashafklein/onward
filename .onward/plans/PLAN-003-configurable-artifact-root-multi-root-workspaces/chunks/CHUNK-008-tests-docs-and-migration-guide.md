---
id: "CHUNK-008"
type: "chunk"
plan: "PLAN-003"
project: ""
title: "Tests, docs, and migration guide"
status: "open"
description: "Update all tests for configurable roots, update docs, write migration guide"
depends_on:
  - "CHUNK-005"
  - "CHUNK-006"
  - "CHUNK-007"
  - "CHUNK-010"
priority: "medium"
effort: "l"
model: "claude-sonnet-4-5"
created_at: "2026-03-21T15:46:48Z"
updated_at: "2026-03-21T15:46:48Z"
---

# Summary

Make the test suite comprehensive for configurable roots and update all user-facing documentation. Ensure backward compatibility is tested and documented.

# Scope

- Update all test files that hardcode `.onward/` paths to work with the new layout (many tests construct paths like `tmp_path / ".onward/plans"`)
- Add new test cases for: single custom root (`root: nb`), multi-root (`roots: {a, b}`), missing `--project` error, combined report
- Add test for template/prompt fallback behavior (project-specific overrides shared)
- Add test for ID uniqueness across multiple roots
- Update `README.md` with `root`/`roots` config documentation
- Update `AGENTS.md` to mention configurable roots
- Update `INSTALLATION.md` with config reference for new keys
- Update `AI_OPERATOR.md` if it references `.onward/` paths
- Update scaffold default config template to show `root` as a commented-out option
- Add migration guide section to docs (how to move from `.onward/` to a custom root)

# Out of scope

- Automated migration tool (move files from `.onward/` to new root)

# Dependencies

- CHUNK-005, CHUNK-006, CHUNK-007 (all code changes complete)

# Expected files/systems involved

- `tests/test_cli_split.py`, `tests/test_cli_work.py`, `tests/test_cli_note.py`, `tests/test_cli_review.py`, `tests/test_cli_scale.py`, `tests/test_cli_lifecycle.py`, `tests/test_plan015_run_records.py`, `tests/test_run_record_io.py`, `tests/test_sync.py`, `tests/test_claimed_task_ids.py`, `tests/test_onboarding_simulation.py`, `tests/test_architecture_seams.py`
- `docs/README.md`, `docs/INSTALLATION.md`, `docs/AI_OPERATOR.md`, `AGENTS.md`
- `src/onward/scaffold.py` (default config template text)

# Completion criteria

- [ ] `pytest` passes with zero failures
- [ ] New tests exist for single custom root, multi-root, and error cases
- [ ] `README.md` documents `root` and `roots` config keys
- [ ] `INSTALLATION.md` lists new config keys
- [ ] Default config template shows `root` as a commented option
- [ ] No documentation references `.onward/` as the only possible artifact location
