---
id: "TASK-056"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-016"
project: ""
title: "cli.py: rename --effort → --complexity on new task and new chunk subcommands"
status: "completed"
description: "In `src/onward/cli.py`, update the `build_parser` function:\n\n1. For the `chunk` subparser (~line 107-116): change `--effort` argument to `--complexity`. Update help text from `\"T-shirt size: xs|s|m|l|xl (invalid values ignored)\"` to `\"Complexity: low|medium|high (invalid values ignored)\"`.\n\n2. For the `task` subparser (~line 151-155): change `--effort` argument to `--complexity`. Update help text from `\"T-shirt size: xs|s|m|l|xl (invalid values ignored)\"` to `\"Complexity: low|medium|high (invalid values ignored)\"`.\n\nThe argparse dest will automatically become `complexity` when the flag is `--complexity`, so `args.complexity` will be used instead of `args.effort` by cli_commands.py (updated in a separate task).\n\nNo other changes needed in cli.py."
human: false
model: "haiku"
executor: "onward-exec"
depends_on: []
files:
- "src/onward/cli.py"
acceptance:
- "onward new task --help shows --complexity option with low|medium|high hint"
- "onward new chunk --help shows --complexity option"
- "--effort flag no longer appears in the task or chunk subparsers"
- "Zero grep matches for '\\-\\-effort' in src/onward/cli.py"
created_at: "2026-03-21T20:23:52Z"
updated_at: "2026-03-21T20:54:33Z"
effort: "xs"
run_count: 1
last_run_status: "completed"
---

# Context

In `src/onward/cli.py`, update the `build_parser` function:

1. For the `chunk` subparser (~line 107-116): change `--effort` argument to `--complexity`. Update help text from `"T-shirt size: xs|s|m|l|xl (invalid values ignored)"` to `"Complexity: low|medium|high (invalid values ignored)"`.

2. For the `task` subparser (~line 151-155): change `--effort` argument to `--complexity`. Update help text from `"T-shirt size: xs|s|m|l|xl (invalid values ignored)"` to `"Complexity: low|medium|high (invalid values ignored)"`.

The argparse dest will automatically become `complexity` when the flag is `--complexity`, so `args.complexity` will be used instead of `args.effort` by cli_commands.py (updated in a separate task).

No other changes needed in cli.py.

# Scope

- In `src/onward/cli.py`, update the `build_parser` function:

1. For the `chunk` subparser (~line 107-116): change `--effort` argument to `--complexity`. Update help text from `"T-shirt size: xs|s|m|l|xl (invalid values ignored)"` to `"Complexity: low|medium|high (invalid values ignored)"`.

2. For the `task` subparser (~line 151-155): change `--effort` argument to `--complexity`. Update help text from `"T-shirt size: xs|s|m|l|xl (invalid values ignored)"` to `"Complexity: low|medium|high (invalid values ignored)"`.

The argparse dest will automatically become `complexity` when the flag is `--complexity`, so `args.complexity` will be used instead of `args.effort` by cli_commands.py (updated in a separate task).

No other changes needed in cli.py.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/cli.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- onward new task --help shows --complexity option with low|medium|high hint
- onward new chunk --help shows --complexity option
- --effort flag no longer appears in the task or chunk subparsers
- Zero grep matches for '\-\-effort' in src/onward/cli.py

# Handoff notes
