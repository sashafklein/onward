---
id: "TASK-038"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-010"
project: ""
title: "Wire split to executor for AI decomposition"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:04Z"
updated_at: "2026-03-20T18:17:36Z"
---

# Context

CHUNK-010 makes `onward split` intelligent by routing decomposition through the AI executor instead of using markdown heuristics. Currently `run_split_model()` in `split.py` uses `_heuristic_split_plan_payload` and `_heuristic_split_chunk_payload` which extract bullet points from markdown sections. This task replaces that with actual executor invocation: the split prompt + artifact body are sent to the executor via subprocess, and the AI response (JSON) is parsed as the split output.

# Scope

- Modify `run_split_model()` in `split.py` to invoke the executor (via subprocess, same pattern as `execution.py`) instead of calling heuristic functions
- Build a split-specific payload: `{type: "split", model, prompt, artifact_metadata, artifact_body, split_type: "plan"|"chunk"}`
- Use `models.split_default` from config (falling back to `models.default`), resolved through `resolve_model_alias`
- Keep `TRAIN_SPLIT_RESPONSE` env override for testing (already exists)
- Keep heuristic functions as fallback behind `--heuristic` flag on `onward split`
- Add `--heuristic` flag to the split subparser in `cli.py`
- Pass the `--heuristic` flag through to `run_split_model` (or select heuristic vs executor path in `cmd_split`)
- Add preflight check before executor invocation (reuse `preflight_ralph_command` pattern)
- Update `cmd_split` in `cli_commands.py` to load config and pass to `run_split_model`

# Out of scope

- Rewriting the split prompt content (TASK-039)
- Output validation and sizing checks (TASK-040)
- Changing the JSON schema that split expects back
- Adding split-specific hooks

# Files to inspect

- `src/onward/split.py` — `run_split_model()` (line ~66), heuristic functions
- `src/onward/cli.py` — split subparser (line ~151), add `--heuristic` flag
- `src/onward/cli_commands.py` — `cmd_split()` (line ~625) to pass config/flags
- `src/onward/execution.py` — reference for subprocess invocation pattern with stdin JSON
- `src/onward/config.py` — `model_setting`, `resolve_model_alias`, `load_workspace_config`
- `src/onward/preflight.py` — `preflight_ralph_command` for pre-execution check
- `tests/test_cli_split.py` — existing split tests (use `TRAIN_SPLIT_RESPONSE` env)

# Implementation notes

- The executor subprocess pattern from `_execute_task_run` in `execution.py` is the reference: build a JSON payload, pipe to stdin, capture stdout, parse JSON from output.
- Split payload should include `schema_version` (reuse `with_schema_version` from `executor_payload.py`).
- The executor receives the split prompt + artifact context and returns JSON matching the `{"chunks": [...]}` or `{"tasks": [...]}` schema.
- `run_split_model` currently takes `(artifact, prompt_name, model, default_task_model)` — it needs additional params: `root` (for config loading) and `heuristic` flag. Update the signature and all callers.
- The prompt file content (`.onward/prompts/split-plan.md` or `split-chunk.md`) should be included in the payload as the instruction.
- If executor invocation fails and `--heuristic` is not set, raise an error (don't silently fall back to heuristics).
- For tests, `TRAIN_SPLIT_RESPONSE` env var already short-circuits — this is the test seam. Add a test that verifies the executor path is attempted when the env var is not set (mock the subprocess).

# Acceptance criteria

- `onward split PLAN-X` invokes the executor (not heuristics) by default
- `onward split CHUNK-X` invokes the executor by default
- `onward split PLAN-X --heuristic` uses the old markdown heuristic path
- Executor receives JSON payload on stdin with `type: "split"`, prompt content, and artifact data
- Split parses JSON response from executor stdout
- Preflight check runs before executor invocation (errors if executor not found)
- `TRAIN_SPLIT_RESPONSE` env override still works for testing
- Existing split tests pass (they use env override)
- New test mocks subprocess to verify executor is called with correct payload

# Handoff notes

- TASK-039 (rewrite prompts) and TASK-040 (validation) build on this. The executor wiring must land first.
- The `executor_payload.py` module may need a new type constant or validation for `"split"` payloads.
- The response parsing (`parse_split_payload`) doesn't change — only the input mechanism changes from heuristics to executor.
