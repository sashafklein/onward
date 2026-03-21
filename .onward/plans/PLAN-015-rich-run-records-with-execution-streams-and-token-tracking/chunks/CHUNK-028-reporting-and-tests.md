---
id: "CHUNK-028"
type: "chunk"
plan: "PLAN-015"
project: ""
title: "Reporting improvements and tests"
status: "completed"
description: ""
priority: "medium"
model: "sonnet-latest"
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:56:28Z"
---

# Summary

Surfaces the new run data in the CLI (`onward show --runs`, `onward report --verbose`)
and adds a comprehensive test suite covering the directory layout, backward compat,
streaming write, git diff computation, and token parsing.

# Scope

- Implement `onward show TASK-* --runs` displaying run history table (timestamps, duration, model, outcome, token counts, file count)
- Add `onward report --verbose` run stats section (total runs, pass rate, total tokens)
- Update `docs/WORK_HANDOFF.md` documenting the new run layout and ack schema v3
- Tests: directory layout, backward compat readers, streaming write, git diff helpers, token extraction

# Out of scope

- Web dashboard (FUTURE_ROADMAP.md)
- Cost/dollar estimation

# Dependencies

- CHUNK-024, CHUNK-025, CHUNK-026, CHUNK-027 (all implementation chunks)

# Expected files/systems involved

- `src/onward/cli_commands.py` — `cmd_show`, `cmd_report`
- `tests/test_run_records.py` (new or extended)
- `docs/WORK_HANDOFF.md`

# Completion criteria

- [ ] `onward show TASK-XXX --runs` outputs a table of all runs with timing and tokens
- [ ] `onward report --verbose` shows aggregate run stats for the current plan
- [ ] All existing tests pass
- [ ] New tests cover: new-layout directory creation, legacy backward compat, streaming line write, `compute_files_changed`, token extraction parser
- [ ] `docs/WORK_HANDOFF.md` documents new run layout and ack v3 schema

# Notes

The `--runs` flag may already exist on `onward show`; if so, extend the existing display rather than adding a new flag.
