---
id: "CHUNK-011"
type: "chunk"
plan: "PLAN-005"
project: ""
title: "Implement WorkReporter class"
status: "in_progress"
description: ""
priority: "medium"
model: "opus-latest"
created_at: "2026-03-21T16:25:51Z"
updated_at: "2026-03-21T16:47:21Z"
---

# Summary

Create the `WorkReporter` class — the self-contained module that knows how to format and emit all progress messages for the `onward work` command. This is the foundation that the rest of the plan wires into the execution path.

# Scope

- Create `src/onward/reporter.py` with the `WorkReporter` class
- Implement all output methods: `status_change`, `working_on`, `completed`, `failed`, `skipped`, `plan_summary`, `info`, `warning`
- Implement indentation via a context manager (`indent()`) for nested plan → chunk → task hierarchy
- Use existing `_colorize()` / `status_color()` from `util.py` for colored output
- Thread-safe `_write()` method using a lock for parallel task safety
- Respect `NO_COLOR` env var and non-tty detection

# Out of scope

- Actually wiring the reporter into cli_commands / execution (that's CHUNK-012)
- JSON output mode, --quiet/--verbose flags
- Rich TUI / progress bars

# Dependencies

None — this is a standalone new module.

# Expected files/systems involved

- `src/onward/reporter.py` (new)
- `src/onward/util.py` (import `_colorize`, `status_color`)

# Completion criteria

- [ ] `WorkReporter` class exists with all documented methods
- [ ] Indentation context manager works for nested output
- [ ] Output uses ANSI colors via existing utilities
- [ ] Thread-safe write method
- [ ] `NO_COLOR` / non-tty detection honored
