---
id: "CHUNK-009"
type: "chunk"
plan: "PLAN-004"
project: ""
title: "Add --md flag and markdown report formatter"
status: "in_progress"
description: "Add --md argument, implement markdown formatter, wire into cmd_report, add tests"
priority: "medium"
effort: "m"
model: "claude-sonnet-4-5"
created_at: "2026-03-21T15:46:49Z"
updated_at: "2026-03-21T16:10:57Z"
---

# Summary

Add the `--md` flag to `onward report` and implement a clean markdown formatter that produces headers, tables, and checkboxes suitable for Obsidian, GitHub, and file piping.

# Scope

- Add `--md` argument to the `report` subparser in `cli.py`
- Implement `format_report_markdown()` function that takes the same computed data as `cmd_report` and returns a markdown string
- Markdown sections: title/header with project + timestamp, Effort Remaining table, In Progress table, Upcoming table, Claimed table (if any), Next item, Blocking Human Tasks table, Recent Completed table, Active Work Tree (fenced code block), Run Stats table (if --verbose)
- Wire into `cmd_report`: if `args.md`, call the formatter and print, then return
- Empty sections render as "*None*" (italic) rather than bare "none"
- `--md` forces no ANSI codes (internal `color_enabled=False`)
- `--md` is orthogonal to `--no-color` and `--project` (all combinations work)
- Add tests: capture output, verify no ANSI escape sequences, verify markdown table structure

# Out of scope

- JSON/YAML/CSV output formats
- Adding `--md` to other commands
- Changing the default (non-`--md`) report format

# Dependencies

None — this can be done independently of PLAN-003.

# Expected files/systems involved

- `src/onward/cli.py` — add `--md` argument
- `src/onward/cli_commands.py` — `cmd_report` branching + `format_report_markdown`
- `tests/test_cli_report.py` or similar — new tests

# Completion criteria

- [ ] `onward report --md` outputs valid markdown with no ANSI escape codes
- [ ] All 8 report sections present in markdown output (9 with verbose)
- [ ] Tables render correctly in GitHub-flavored markdown
- [ ] `--md --project <key>` filters correctly
- [ ] `--md --verbose` includes run stats as markdown table
- [ ] `--md --no-color` does not error
- [ ] New test verifies no `\033[` sequences in `--md` output
- [ ] New test verifies presence of markdown headers (`##`) and table separators (`|---|`)
- [ ] Existing report tests pass unchanged
