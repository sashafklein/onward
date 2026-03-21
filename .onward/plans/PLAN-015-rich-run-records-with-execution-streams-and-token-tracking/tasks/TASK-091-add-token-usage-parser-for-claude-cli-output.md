---
id: "TASK-091"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-027"
project: ""
title: "Add token usage parser for Claude CLI output"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: ["TASK-090"]
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:40:00Z"
---

# Context

Claude CLI prints a usage summary to stderr at the end of execution. This task adds
a best-effort parser that extracts `input_tokens` and `output_tokens` from that
output and populates `ExecutorResult.token_usage` in `BuiltinExecutor`.

# Scope

- Add `extract_token_usage(stderr_output: str) -> dict | None` to `executor_builtin.py`
- Try two strategies in order:
  1. Parse final NDJSON line for a `result` message with `usage` field (if `--output-format stream-json` is used)
  2. Regex-match the plain-text summary line (e.g., `"Input tokens: 12345, Output tokens: 6789"`)
- Return `None` if neither strategy succeeds
- Call `extract_token_usage` on the combined stderr after the subprocess completes
- Set `ExecutorResult.token_usage` from the result (ack-provided usage takes precedence if both are present)

# Out of scope

- Changing Claude CLI invocation flags (no `--output-format` change unless it's already used)
- Cursor CLI token extraction (not available; stays `None`)

# Files to inspect

- `src/onward/executor_builtin.py` — `BuiltinExecutor.execute_task`, stderr collection
- Run an actual `claude` invocation locally to inspect actual stderr format before committing to a regex

# Implementation notes

- Wrap the entire parser in try/except — any parsing failure returns `None`
- The regex is intentionally narrow to avoid false matches from user output
- `total_tokens = input_tokens + output_tokens` computed locally; `model` from ack or `None`

# Acceptance criteria

- [ ] `extract_token_usage` returns a dict for known Claude CLI output formats
- [ ] Returns `None` for unrecognized or empty output
- [ ] Unit tests with sample stderr strings (both NDJSON and plain-text patterns)
- [ ] `info-*.json` contains `token_usage` after a real Claude CLI run (manual verification ok)

# Handoff notes

This is best-effort. If the Claude CLI format changes, the parser silently returns `None` and execution continues normally.
