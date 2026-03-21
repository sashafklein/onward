---
id: "TASK-060"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-016"
project: ""
title: "Implement CLI routing with Claude and Cursor backends"
status: "completed"
description: "Create CLIBackend base, ClaudeBackend, CursorBackend, and route_model_to_backend pattern matcher."
human: false
model: "composer-2"
effort: "medium"
depends_on: []
files:
- "src/onward/executor_builtin.py"
acceptance:
- "ClaudeBackend builds argv for claude CLI"
- "CursorBackend builds argv for cursor CLI"
- "route_model_to_backend routes opus/sonnet/haiku/claude-* to ClaudeBackend"
- "route_model_to_backend routes cursor-* to CursorBackend"
- "Unknown models default to ClaudeBackend"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:29:57Z"
run_count: 1
last_run_status: "completed"
---

# Context

The routing layer that maps model strings to concrete CLI invocations. This is the core of the built-in executor -- everything else calls through this.

# Scope

- Create `src/onward/executor_builtin.py`
- `CLIBackend` base class (or ABC):
  - `name: str` property
  - `build_argv(self, model: str, prompt: str) -> list[str]`
  - `find_executable(self) -> str | None` (uses `shutil.which`)
- `ClaudeBackend(CLIBackend)`:
  - `build_argv` -> `["claude", "--model", model, "-p", prompt]`
- `CursorBackend(CLIBackend)`:
  - `build_argv` -> `["cursor", "--agent", "--model", model, "-p", prompt]` (verify exact flags)
- `route_model_to_backend(model: str) -> CLIBackend`:
  - Pattern matching on lowercased model string
  - `claude`, `opus`, `sonnet`, `haiku` -> ClaudeBackend
  - `cursor`, `gemini` -> CursorBackend
  - Default -> ClaudeBackend
- Unit tests for routing patterns

# Out of scope

- BuiltinExecutor class (TASK-062)
- Prompt building (TASK-061)
- Streaming output handling (TASK-062)

# Files to inspect

- `scripts/onward-exec` -- `_model_uses_claude_cli()` for current routing logic
- Cursor CLI docs for exact agent flags

# Implementation notes

- Keep routing patterns simple and extensible (a list of (pattern, backend) tuples)
- `find_executable` should return None if CLI not on PATH (caller decides what to do)
- Consider making backends singletons since they're stateless

# Acceptance criteria

- [ ] `route_model_to_backend("opus-latest").name` == `"claude"`
- [ ] `route_model_to_backend("sonnet-latest").name` == `"claude"`
- [ ] `route_model_to_backend("cursor-fast").name` == `"cursor"`
- [ ] `route_model_to_backend("unknown-model").name` == `"claude"` (default)
- [ ] `ClaudeBackend().build_argv("opus-latest", "do X")` produces correct argv
- [ ] `CursorBackend().build_argv("cursor-fast", "do X")` produces correct argv
