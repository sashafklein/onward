---
id: "TASK-034"
type: "task"
plan: "PLAN-004"
chunk: "CHUNK-009"
project: ""
title: "Wire --md into cmd_report and add tests"
status: "completed"
description: "Branch cmd_report on args.md, call formatter, add tests for no-ANSI and valid markdown"
human: false
model: "claude-sonnet-4-5"
effort: "s"
depends_on:
- "TASK-033"
files:
- "src/onward/cli_commands.py"
- "tests/test_cli_report_md.py"
acceptance:
- "onward report --md produces markdown output"
- "onward report (without --md) produces ANSI output unchanged"
- "Test captures --md output and verifies no \\033[ sequences"
- "Test verifies ## headers and |---| table separators"
- "--md with --project filters correctly"
- "--md with --verbose includes run stats"
- "--md with --no-color does not error"
created_at: "2026-03-21T15:50:10Z"
updated_at: "2026-03-21T16:20:49Z"
run_count: 1
last_run_status: "completed"
---

# Context

This task adds comprehensive tests for the markdown report output feature (`--md` flag) that was implemented in TASK-033.

# Scope

- Create `tests/test_cli_report_md.py` with comprehensive test coverage
- Verify no ANSI escape sequences in markdown output
- Verify proper markdown structure (headers, tables, separators)
- Test interaction with `--project`, `--verbose`, and `--no-color` flags
- Ensure existing report tests still pass (regression testing)

# Out of scope

- Modifying the implementation (already done in TASK-033)
- JSON/YAML/CSV output formats
- Adding `--md` to other commands

# Files to inspect

- `src/onward/cli_commands.py` (lines 1363-1606) - implementation already done
- `tests/test_cli_note.py` - example test pattern
- Existing tests using `report` command

# Implementation notes

- TASK-033's handoff notes indicated the function was already wired into `cmd_report`, so this task focused entirely on testing
- Used `capsys` fixture to capture stdout for verification
- Pattern matches existing test style in the codebase
- All table separators use `|---|` format (GitHub-flavored markdown)

# Acceptance criteria

✅ All acceptance criteria met:
- ✅ `onward report --md` produces markdown output
- ✅ `onward report` (without --md) produces ANSI output unchanged
- ✅ Test captures --md output and verifies no `\033[` sequences
- ✅ Test verifies `##` headers and `|---|` table separators
- ✅ `--md` with `--project` filters correctly
- ✅ `--md` with `--verbose` includes run stats
- ✅ `--md` with `--no-color` does not error

# Handoff notes

**Testing complete** - Created `tests/test_cli_report_md.py` with 11 comprehensive tests:

1. `test_md_flag_produces_markdown_no_ansi` - Verifies no ANSI escape codes
2. `test_md_has_valid_structure` - Checks all required sections and table format
3. `test_md_with_project_filter` - Tests `--project` filtering
4. `test_md_with_verbose_includes_run_stats` - Verifies run stats section with `--verbose`
5. `test_md_without_verbose_no_run_stats` - Ensures no run stats without `--verbose`
6. `test_md_with_no_color_does_not_error` - Tests flag orthogonality
7. `test_default_report_without_md_unchanged` - Regression test for default output
8. `test_md_empty_sections_show_none` - Verifies `*None*` for empty sections
9. `test_md_tables_have_proper_format` - Validates table structure
10. `test_md_active_work_tree_as_code_block` - Checks code fence rendering
11. `test_md_output_is_pipeable` - Verifies output can be written to files

**Test results:**
- All 11 new tests pass ✅
- All 7 existing tests using `report` command still pass ✅
- Verified manually: no ANSI codes, proper markdown structure, filtering works

**PLAN-004 is now complete** - The `--md` flag is fully implemented, tested, and ready for use.
