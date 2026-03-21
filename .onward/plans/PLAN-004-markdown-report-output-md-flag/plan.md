---
id: "PLAN-004"
type: "plan"
project: ""
title: "Markdown report output (--md flag)"
status: "completed"
description: ""
priority: "medium"
model: "claude-opus-4-5"
created_at: "2026-03-21T15:44:38Z"
updated_at: "2026-03-21T16:20:49Z"
---

# Summary

Add a `--md` flag to `onward report` that emits clean markdown instead of ANSI-colored terminal text. This makes reports pipeble to files, renderable in Obsidian, and usable as dashboard input.

# Problem

`onward report` outputs ANSI-colored terminal text. Users want clean markdown output they can pipe to a file or render in Obsidian dashboards. There is no way to get structured, portable output today (even `--no-color` still outputs tab-separated plain text, not markdown).

# Goals

- Add `--md` flag to `onward report`
- Output clean markdown with headers, tables, and checkboxes — no ANSI codes
- Compatible with `--project` filtering
- Compatible with `--verbose` (run stats section)
- Output suitable for piping to a file (`onward report --md > report.md`)

# Non-goals

- JSON/YAML/CSV output formats (future work)
- Adding `--md` to other commands (just `report` for now)
- Changing the default (non-`--md`) report output format

# End state

- [ ] `onward report --md` outputs valid, clean markdown to stdout
- [ ] `onward report --md --project nb` scopes markdown to one project
- [ ] `onward report --md --verbose` includes run stats as a markdown table
- [ ] Output renders correctly in Obsidian and GitHub markdown viewers
- [ ] Piping to a file produces a clean `.md` file

# Context

The report is generated in `cmd_report()` in `cli_commands.py` (lines 1363–1558). It calls helper functions (`report_rows`, `summarize_effort_remaining`, `select_next_artifact`, `render_active_work_tree_lines`, `claimed_rows`, `collect_runs_for_target`) and uses `colorize()` from `util.py` for ANSI formatting.

The current structure has 8 sections: Effort Remaining, In Progress, Upcoming, Claimed, Next, Blocking Human Tasks, Recent Completed, Active Work Tree, and optionally Run Stats. Each section uses tab-separated rows with status coloring.

# Proposed approach

## 1. Add `--md` argument

In `cli.py`, add `--md` to the `report` subparser:

```python
report_parser.add_argument("--md", action="store_true", default=False, help="Output clean markdown instead of ANSI")
```

## 2. Markdown formatter function

Create a `format_report_markdown()` function (in `cli_commands.py` or a new `report_format.py` if we want separation). This function takes the same data that `cmd_report` computes and returns a markdown string.

Markdown structure:

```markdown
# Onward Report

**Project:** nb (if filtered)
**Generated:** 2026-03-21T15:00:00Z

## Effort Remaining

| xs | s | m | l | xl | unestimated |
|----|---|---|---|----|-------------|
| 0  | 2 | 1 | 0 | 0  | 3           |

## In Progress

| ID | Type | Status | Title | File |
|----|------|--------|-------|------|
| TASK-012 | task | in_progress | Implement widget | .onward/plans/... |

## Upcoming

| ID | Type | Status | Title | File |
|----|------|--------|-------|------|
| TASK-013 | task | open | Add tests | .onward/plans/... |

## Next

- **TASK-013** (task, open): Add tests

## Blocking Human Tasks

| ID | Status | Title | File |
|----|--------|-------|------|
(or "None")

## Recent Completed

| Completed | Breadcrumb | Title |
|-----------|------------|-------|
| 2026-03-21T04:30:32Z | PLAN-002 | Fix design concerns |

## Active Work Tree

(Preserve tree indentation as a code block or nested list)

## Run Stats (--verbose only)

| Metric | Value |
|--------|-------|
| Total runs | 5 (3 completed, 2 failed) |
| Pass rate | 60.0% |
| Total tokens | 12.3k input / 4.5k output |
```

## 3. Wire into cmd_report

In `cmd_report`, after computing all the data (artifacts, blockers, rows, etc.), check `args.md`:

```python
if getattr(args, "md", False):
    md = format_report_markdown(...)
    print(md)
    return 0
```

The existing ANSI path remains the default.

## 4. Active work tree rendering

`render_active_work_tree_lines()` currently returns lines with ANSI color and tree-drawing characters. For markdown mode, either:
- Pass `color_enabled=False` and wrap in a fenced code block (preserves tree characters)
- Or render as a nested markdown list

A fenced code block is simpler and preserves the visual tree structure.

# Acceptance criteria

1. `onward report --md` produces clean markdown (no ANSI escape codes)
2. All 8 report sections are present in the markdown output (9 with `--verbose`)
3. `--md` with `--project` correctly filters
4. `--md` with `--verbose` includes run stats as a markdown table
5. Output renders correctly in GitHub-flavored markdown
6. `--md` with `--no-color` does not error (flags are orthogonal)
7. New test: capture markdown output and verify no ANSI codes, valid structure
8. Existing report tests are not broken

# Notes

- The `--md` flag should force `color_enabled=False` internally (no ANSI codes in markdown).
- Consider using `datetime.utcnow().isoformat()` for the "Generated" timestamp in the header.
- The "none" placeholder for empty sections should render as italic "*None*" in markdown.
