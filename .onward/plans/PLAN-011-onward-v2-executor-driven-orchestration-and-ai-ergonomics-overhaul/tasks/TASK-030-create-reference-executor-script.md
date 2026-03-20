---
id: "TASK-030"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-008"
project: ""
title: "Create reference executor script"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on:
  - "TASK-029"
blocked_by: []
files:
  - "scripts/onward-exec"
acceptance:
  - "scripts/onward-exec exists and is executable"
  - "scripts/onward-exec --help prints usage"
  - "echo valid JSON payload | scripts/onward-exec processes without crash"
created_at: "2026-03-20T16:00:56Z"
updated_at: "2026-03-20T16:42:44Z"
---

# Context

With the ralph→executor rename complete (TASK-029), the config now points to `executor.command: onward-exec` by default. This task creates the actual `scripts/onward-exec` script — a thin Python routing layer that reads the executor payload from stdin, extracts the model and task context, and invokes the appropriate AI CLI tool (e.g., `claude` for Claude models). This is the bridge between Onward's orchestration and the actual AI model execution.

# Scope

- Create `scripts/onward-exec` as an executable Python script (~100-150 lines)
- Read JSON payload from stdin (the executor payload as defined by `execution.py`)
- Support payload types: `task`, `hook`, `review`
- For `task` type: extract task body, chunk context, plan context, notes; build a prompt; invoke AI CLI
- For `hook` type: extract hook body and context; invoke AI CLI with the hook prompt
- For `review` type: extract plan body and review prompt; invoke AI CLI
- Route based on model name:
  - Models containing "claude" or matching known Claude aliases → invoke `claude` CLI: `claude --model MODEL -p "PROMPT"`
  - Provide a clear extension point for other models (e.g., a comment block showing where to add codex/gpt routing)
- Pass through stdout/stderr from the invoked CLI tool
- Exit with the child process exit code
- When `ONWARD_RUN_ID` is set in environment, emit a success ack JSON line on successful completion (matching the `onward-task-success-ack-v1` schema)
- Add `--help` / `--version` flags for discoverability
- Add `--dry-run` flag that prints the constructed prompt without executing

# Out of scope

- Multi-model orchestration or automatic fallback (the script routes to one tool per invocation)
- Token counting or cost tracking
- Streaming output (capture and forward is fine)
- Interactive mode or REPL
- Installing or managing the `claude` CLI itself
- Provider registry or plugin system (future CHUNK work)

# Files to inspect

- `src/onward/execution.py` — understand the payload shape sent to the executor (the `payload` dict in `_execute_task_run`, `_run_markdown_hook`, `execute_plan_review`)
- `src/onward/executor_payload.py` — `with_schema_version` adds schema version to payloads
- `src/onward/executor_ack.py` — `find_task_success_ack` defines what a success ack looks like
- `docs/schemas/onward-task-success-ack-v1.schema.json` — the ack schema
- `docs/WORK_HANDOFF.md` — executor bridge documentation (will be updated in TASK-033)

# Implementation notes

- **Shebang**: `#!/usr/bin/env python3` — no dependencies beyond stdlib
- **Payload parsing**: `json.load(sys.stdin)`. If stdin is empty or invalid JSON, exit with code 1 and a clear error to stderr.
- **Prompt construction for tasks**: Concatenate in this order:
  1. Plan context (title, summary) if present — gives the AI the big picture
  2. Chunk context (title, scope) if present — gives the immediate goal
  3. Task body (the full markdown) — the actual instructions
  4. Notes if present — additional context from `onward note`
  5. A footer reminding the AI to report completion status
- **Claude CLI invocation**: `subprocess.run(["claude", "--model", model, "-p", prompt], ...)`. Check `shutil.which("claude")` first; if not found, print a clear error.
- **Success ack emission**: After the child process exits 0, print a JSON line to stdout: `{"schema": "onward-task-success-ack-v1", "run_id": run_id, "status": "completed", "message": "..."}`. The `run_id` comes from `payload["run_id"]` or `os.environ.get("ONWARD_RUN_ID")`.
- **Error handling**: Wrap subprocess calls in try/except. If the CLI tool is not found, suggest installation. If it exits non-zero, pass through the exit code.
- **Keep it simple**: This is a routing script, not a framework. Resist the urge to add abstraction layers. A flat `main()` with clear if/elif branches is preferred over class hierarchies.
- **Testing**: The script can be tested by piping a JSON payload and checking exit code. Consider adding a `--dry-run` mode that prints the prompt to stdout without invoking the AI CLI — useful for testing and debugging.

# Acceptance criteria

- `scripts/onward-exec` exists with `chmod +x` and `#!/usr/bin/env python3` shebang
- `echo '{"type":"task","run_id":"RUN-test","task":{"id":"TASK-001"},"body":"say hello","schema_version":"onward-executor-payload-v1"}' | python3 scripts/onward-exec --dry-run` prints a constructed prompt to stdout without invoking any external CLI
- The script handles missing `claude` CLI gracefully (clear error message, exit code 1)
- The script handles invalid/empty stdin gracefully (clear error message, exit code 1)
- When ONWARD_RUN_ID is set and child process exits 0, a valid success ack JSON line appears in stdout
- The script is pure stdlib Python — no pip dependencies
- `python3 scripts/onward-exec --help` prints usage information

# Handoff notes

This script is intentionally minimal. Future chunks will add provider registry support (CHUNK for provider interop) that may replace the hardcoded claude CLI routing. For now, the script demonstrates the executor contract and enables dogfooding. If you discover that the payload shape from execution.py is missing fields you need, note them — they should be added in a follow-up task, not by modifying execution.py in this task.
