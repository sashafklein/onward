---
id: "PLAN-011"
type: "plan"
project: ""
title: "Onward v2: executor-driven orchestration and AI ergonomics overhaul"
status: "open"
description: "Overhaul Onward from a task tracker into a real AI orchestration tool with working executor integration, intelligent splitting, structured feedback, and multi-agent coordination."
priority: "high"
model: "opus-latest"
created_at: "2026-03-20T15:50:24Z"
updated_at: "2026-03-20T15:50:24Z"
---

# Summary

Onward currently has the right mental model (Plan → Chunk → Task, file-backed, git-native) but the executor integration is a stub, split doesn't use AI, there's no structured feedback from execution, and the status model has gaps that confuse AI agents. This plan overhauls Onward into a tool that can actually orchestrate AI agents: a configurable executor that routes to cursor/claude-code based on model, intelligent plan and chunk splitting, a `failed` status with circuit breakers, unified dependency tracking, batch operations, and multi-project awareness. The first chunk enables dogfooding so subsequent work can be executed by Onward itself.

# Problem

1. **No working executor.** `onward work` shells out to "ralph" but ralph is hardcoded and undefined. There's no reference executor script that actually spawns AI agents. The system can't do real work.
2. **Split is a stub.** `onward split` does markdown heuristics, not AI decomposition. The prompts exist but aren't wired up. This is the most valuable AI-facing feature and it doesn't work.
3. **Status model has gaps.** Failed tasks go back to `open` (indistinguishable from never-attempted). No circuit breaker. `depends_on` vs `blocked_by` is a trap. `onward start` is vestigial.
4. **No structured feedback.** The executor can only return exit 0/1. No way to report partial progress, discovered work, or files changed.
5. **No batch/scale operations.** Creating 10 tasks requires 10 CLI calls. No `onward ready`. No effort metadata. `index.yaml` is write-only.
6. **Model resolution is wrong-layer.** Onward resolves model aliases when the executor should.
7. **Custom YAML parser is fragile.** Hand-rolled parser doesn't handle edge cases that AI-generated frontmatter hits.

# Goals

- An AI orchestrator can run `onward work PLAN-011` and have the entire plan executed, chunk by chunk, task by task, with appropriate models routed to appropriate tools
- `onward split` produces intelligent, self-contained, right-sized chunks and tasks using AI
- Failed tasks are visible, retry-limited, and don't poison `onward next`
- An executor can report structured results (files changed, follow-up work, partial progress)
- Multiple plans across multiple projects can be tracked and filtered
- Batch task creation for rapid enqueuing
- `onward ready` shows actionable work across all open plans
- Commit-after-task is a default behavior
- The system dogfoods itself: later chunks in this plan are executed by the executor built in the first chunk

# Non-goals

- Parallel task execution within a chunk (future work; tasks within a chunk are sequential for now)
- Long-running daemon or job queue (file-backed coordination is sufficient)
- GUI or web interface
- Support for non-AI executors (scripts are fine, but the primary use case is AI agents)

# End state

- [ ] `onward work TASK-X` spawns an AI agent (via configured executor script) that completes the task, commits, and reports structured results
- [ ] `onward work CHUNK-X` drains all tasks in dependency order, auto-completes the chunk
- [ ] `onward work PLAN-X` drains all chunks in order, auto-completes the plan
- [ ] `onward split PLAN-X` uses AI to produce well-sized, self-contained chunks following the nb patterns
- [ ] `onward split CHUNK-X` uses AI to produce atomic, file-targeted tasks following the plan-to-beads patterns
- [ ] `onward ready` shows all actionable work across plans/projects
- [ ] `onward new task CHUNK-X --batch tasks.json` creates multiple tasks at once
- [ ] Failed tasks show as `failed`, with retry count tracked, configurable circuit breaker
- [ ] `depends_on` is the single dependency mechanism, clearly documented
- [ ] `onward start` is removed
- [ ] Executor reports structured results: `{files_changed, follow_ups, summary}`
- [ ] Default post-task hook commits changes
- [ ] `--project` filtering works throughout, multi-project metadata is first-class
- [ ] `index.yaml` is used for reads where appropriate (fast path)
- [ ] Model resolution is executor-side, not in Onward core
- [ ] PyYAML replaces custom parser
- [ ] Recovery docs explain what to do when execution fails

# Context

This plan draws on patterns from the `nb` repo's delivery pipeline:
- `plan-to-beads.md`: Task decomposition with self-containment rules, <=6 file target per task, model labels, bead sizing
- `chunk.md`: Chunk decomposition with 20-30 file target, file touch maps, dependency DAGs, acceptance criteria
- `work.md`: Execution discipline with TODO capture, gap discovery, commit frequency, end-of-session checklists

The current Onward system already has the right hierarchy and file format. The gap is in execution (no working executor), intelligence (split is heuristic), and robustness (status model, feedback, scale).

# Proposed approach

## Chunk 1: Executor foundation (enables dogfooding)

This is the critical path. Everything else can be dogfooded once this works.

### 1a. Abstract "ralph" to "executor" throughout codebase

- Rename config key from `ralph` to `executor` (keep `ralph` as deprecated alias)
- Replace all hardcoded "ralph" strings in source, tests, docs
- Config shape: `executor: { command: "onward-exec", args: [], enabled: true }`
- Task metadata: `executor: "onward-exec"` (or omit to use default)

### 1b. Create reference executor script `scripts/onward-exec`

A shell/Python script that:
- Reads JSON payload from stdin
- Extracts `type` (task/hook/review), `task.model`, task body, context
- Routes based on model family:
  - claude-* models → `claude` CLI with appropriate flags
  - cursor-* / codex-* → cursor agent mode (or codex CLI)
  - Fallback → configurable default
- Passes task context as system prompt + user message
- Includes instructions to commit on completion
- Captures output, streams to stdout
- Exits 0 on success, non-zero on failure
- Emits structured ack JSON on success when `ONWARD_RUN_ID` is set

### 1c. Make `onward work PLAN-*` work

Currently only task and chunk are supported. Add plan-level execution:
- Set plan to `in_progress`
- Iterate chunks in dependency order (use `depends_on` on chunks)
- For each chunk, run `work_chunk` logic
- Auto-complete plan when all chunks are terminal

### 1d. Default commit hook

- Add a default `post_task_shell` hook that runs `git add -A && git commit -m "onward: completed TASK-XXX"`
- Make this the scaffold default (opt-out, not opt-in)
- The commit message should include the task ID and title

### 1e. Update scaffold and docs

- `onward init` produces the new config shape
- AGENTS.md, INSTALLATION.md, WORK_HANDOFF.md updated
- LIFECYCLE.md updated for plan-level work

Files: `src/onward/config.py`, `src/onward/execution.py`, `src/onward/cli_commands.py`, `src/onward/scaffold.py`, `scripts/onward-exec`, `docs/WORK_HANDOFF.md`, `docs/LIFECYCLE.md`, `INSTALLATION.md`, `AGENTS.md`, tests

## Chunk 2: Status model cleanup

### 2a. Add `failed` status

- New terminal-ish status: `failed` (task attempted, executor returned failure)
- `onward work` sets task to `failed` on executor failure (not back to `open`)
- `failed` tasks are excluded from `onward next` recommendations
- `onward retry TASK-X` resets a failed task to `open` (explicit intent to retry)
- Track `run_count` and `last_run_status` in frontmatter for visibility

### 2b. Circuit breaker

- Config: `work.max_retries: 3` (default)
- `onward work` checks run count before executing; refuses if exceeded
- `onward work CHUNK-X` skips failed-and-maxed tasks, continues with others
- Clear error message: "TASK-X has failed 3 times; run `onward retry TASK-X` to reset"

### 2c. Kill `onward start`

- Remove `start` subcommand from CLI
- Remove `start` transition from `transition_status`
- The `in_progress` state is now only set by `onward work` (machine-managed)
- Update all docs, AGENTS.md, tests

### 2d. Unify `depends_on` / `blocked_by`

- `depends_on` is the single mechanism: task X depends on task Y being completed
- `blocked_by` becomes a deprecated alias that maps to `depends_on` on read
- `task_is_next_actionable` uses only `depends_on` with completion checking
- Document clearly in LIFECYCLE.md

Files: `src/onward/artifacts.py`, `src/onward/execution.py`, `src/onward/cli.py`, `src/onward/cli_commands.py`, `docs/LIFECYCLE.md`, tests

## Chunk 3: Intelligent split

### 3a. Wire split to executor

- `onward split PLAN-X` sends the plan body + split prompt to the executor
- `onward split CHUNK-X` sends the chunk body + split prompt to the executor
- Use `models.split_default` (default: sonnet) for split operations
- Remove heuristic fallback (or keep as `--heuristic` flag for offline use)

### 3b. Port nb split instructions

- Replace `.onward/prompts/split-plan.md` with adapted content from `nb/chunk.md`:
  - 20-30 file target per chunk
  - File touch maps (must/likely/deferred)
  - Dependency DAG validation
  - Acceptance criteria per chunk
  - Self-containment requirements
- Replace `.onward/prompts/split-chunk.md` with adapted content from `nb/plan-to-beads.md`:
  - <=6 file target per task
  - Self-containment rules (specific file paths, inline context, no "see plan")
  - Model label suggestions (haiku/sonnet/opus based on complexity)
  - Sizing validation (warning at 7-9 files, split if >9)

### 3c. Split output validation

- Validate executor JSON output matches expected schema
- Check chunk/task count, sizing, dependency structure
- Dry-run mode shows what would be created with validation warnings

Files: `src/onward/split.py`, `.onward/prompts/split-plan.md`, `.onward/prompts/split-chunk.md`, `src/onward/execution.py`, tests

## Chunk 4: Structured feedback and recovery

### 4a. Executor result schema

Define and implement structured results from executor:
```json
{
  "onward_task_result": {
    "status": "completed",
    "schema_version": 1,
    "run_id": "RUN-...",
    "summary": "Implemented retry logic with 3 attempts",
    "files_changed": ["src/onward/execution.py", "tests/test_retry.py"],
    "follow_ups": [
      {"title": "Add exponential backoff", "description": "...", "priority": "low"}
    ],
    "acceptance_met": ["retry logic works", "tests pass"],
    "acceptance_unmet": []
  }
}
```

- Onward parses this on success and stores on run record
- `follow_ups` are auto-created as new tasks in the current chunk
- `files_changed` stored for audit/display
- `acceptance_met`/`acceptance_unmet` shown in `onward show`

### 4b. Recovery documentation

- New `docs/RECOVERY.md`: what to do when execution fails
  - Read the run log: `onward show TASK-X` → log path
  - Common failure modes and fixes
  - How to retry: `onward retry TASK-X` then `onward work TASK-X`
  - How to skip: `onward cancel TASK-X` and create follow-up
  - How to intervene: edit task body, adjust acceptance criteria, re-run

### 4c. `onward show` improvements

- Show run history (not just latest run)
- Show retry count
- Show structured results from last successful run
- Show dependency graph (what this task blocks/is blocked by)

Files: `src/onward/executor_ack.py`, `src/onward/execution.py`, `src/onward/cli_commands.py`, `docs/RECOVERY.md`, `docs/schemas/`, tests

## Chunk 5: Scale and ergonomics

### 5a. Batch task creation

- `onward new task CHUNK-X --batch tasks.json` creates multiple tasks from a JSON array
- Each entry: `{title, description, model, human, depends_on, files, acceptance, effort}`
- IDs assigned sequentially
- Single index regeneration at end

### 5b. `onward ready` command

- Shows all open plans with their first ready chunk and first ready task
- Grouped by project (if set)
- Includes effort estimates if available
- Essentially: "here's everything you could start working on right now"

### 5c. Effort/size metadata

- Add `effort` field to task/chunk metadata: `xs`, `s`, `m`, `l`, `xl`
- Add `estimated_files` to chunk metadata
- `onward report` shows aggregate effort remaining
- `onward ready` sorts by effort (smallest first, for quick wins)

### 5d. Multi-project filtering

- `--project` flag on all read commands (already partially done)
- `onward report --project myapp` scopes everything
- `onward ready --project myapp` shows only that project
- Project is inherited: tasks inherit project from chunk, chunk from plan (unless overridden)

### 5e. Use index.yaml for fast reads

- `onward list`, `onward ready`, `onward next` read from `index.yaml` when available
- Fall back to full scan if index is missing or stale
- Add `index_version` counter to detect staleness

Files: `src/onward/cli.py`, `src/onward/cli_commands.py`, `src/onward/artifacts.py`, tests

## Chunk 6: Infrastructure cleanup

### 6a. Replace custom YAML with PyYAML

- Add `pyyaml` to dependencies
- Replace `parse_simple_yaml` / `dump_simple_yaml` with PyYAML
- Keep `split_frontmatter` (it's just string splitting)
- Update all tests

### 6b. Move model resolution to executor

- Remove `MODEL_FAMILIES` and `resolve_model_alias` from `config.py`
- Executor script handles model name resolution
- Onward passes through whatever model string is in config/frontmatter
- Config `models.*` keys remain for default model selection, just no alias resolution

### 6c. Clean up hook system

- Remove `pre_task_markdown` (unused, null by default)
- Keep: `pre_task_shell`, `post_task_shell`, `post_task_markdown`, `post_chunk_markdown`
- Document the 4 remaining hooks clearly in WORK_HANDOFF.md
- Add `pre_chunk_shell` for symmetry

### 6d. FUTURE_ROADMAP.md

Create a parking lot for deferred work:
- Parallel task execution within chunks (worktree-per-task)
- Incremental index regeneration
- Daemon mode for long-running orchestration
- Worktree-per-chunk for parallel chunk execution
- Cross-workspace dependencies
- Web dashboard for oversight

Files: `pyproject.toml`, `src/onward/util.py`, `src/onward/config.py`, `src/onward/execution.py`, `src/onward/scaffold.py`, `docs/FUTURE_ROADMAP.md`, tests

# Key artifacts

- `scripts/onward-exec` — reference executor script (new)
- `docs/RECOVERY.md` — failure recovery guide (new)
- `docs/FUTURE_ROADMAP.md` — deferred work parking lot (new)
- `docs/schemas/onward-task-result-v2.schema.json` — structured result schema (new)
- `.onward/prompts/split-plan.md` — overhauled with nb patterns
- `.onward/prompts/split-chunk.md` — overhauled with nb patterns

# Acceptance criteria

- [ ] `onward work TASK-X` spawns a real AI agent that modifies code and commits
- [ ] `onward work CHUNK-X` completes all tasks and auto-completes chunk
- [ ] `onward work PLAN-X` completes all chunks and auto-completes plan
- [ ] `onward split PLAN-X` produces intelligent chunks via AI (not heuristics)
- [ ] `onward split CHUNK-X` produces self-contained tasks via AI
- [ ] Failed tasks show `failed` status; `onward next` skips them
- [ ] Circuit breaker stops after configurable max retries
- [ ] `onward start` is gone; `in_progress` is machine-managed
- [ ] `depends_on` is the single dependency field; `blocked_by` is deprecated alias
- [ ] Executor emits structured results; follow-ups auto-created as tasks
- [ ] `onward ready` shows actionable work across plans/projects
- [ ] Batch task creation works
- [ ] PyYAML replaces custom parser; all tests pass
- [ ] Model resolution removed from Onward core
- [ ] `docs/RECOVERY.md` exists and is referenced from AGENTS.md
- [ ] Dogfood: chunks 3+ of this plan are executed by the executor from chunk 1

# Notes

Execution order matters. Chunk 1 must land first because it enables dogfooding. Chunks 2-6 have light dependencies on each other but can mostly be reordered. Chunk 2 (status cleanup) should come before chunk 4 (feedback) since the `failed` status is needed for structured results. Chunk 3 (split) is independent. Chunk 5 (scale) is independent. Chunk 6 (cleanup) should be last since it's lowest risk and least urgent.

The reference executor script (`scripts/onward-exec`) is intentionally simple — it's a routing layer, not a framework. It reads the model from the payload, picks the right CLI tool, and passes context. The intelligence lives in the AI model, not the script.
