---
id: "PLAN-015"
type: "plan"
project: ""
title: "Rich run records with execution streams and token tracking"
status: "completed"
description: "Restructure run records into per-task folders with live output streaming, multi-run support, and optional token usage tracking"
priority: "medium"
model: "opus-latest"
created_at: "2026-03-21T00:21:37Z"
updated_at: "2026-03-21T03:56:55Z"
---

# Summary

Run records today are opaque: a metadata JSON written at completion and a log that
captures the summary output — but nothing about what the AI was doing or thinking
during execution. Investigating a failed or slow task requires guessing. This plan
restructures runs into per-task folders with three files (metadata, summary, live
output stream), supports multiple runs per task (retries), and adds optional token
usage tracking for cost analysis and model selection tuning.

# Problem

**Opaque execution.** The `.log` file for a run is written once at the end
(`run_log.write_text(...)` in `_run_hooked_executor_batch`). During a long-running
task, there's no way to see what the executor is doing. The `BuiltinExecutor` streams
stdout/stderr to the terminal via `_tee_stream`, but that output only reaches the
run log after the task completes (or fails). If you're monitoring from another
terminal, the run log doesn't exist yet.

**Flat file structure.** Runs are `RUN-<timestamp>-<task-id>.json` and
`RUN-<timestamp>-<task-id>.log` in a flat `.onward/runs/` directory. With retries,
a single task may have multiple pairs. Globbing `RUN-*-TASK-020.*` works but is
awkward, and the directory gets cluttered fast.

**Empty `task_result`.** The `files_changed`, `summary`, `acceptance_met`, etc.
fields in `task_result` are almost always empty because the executor (Claude CLI)
doesn't emit structured `onward_task_result` JSON with those fields populated. The
`BuiltinExecutor` only captures the ack line, which is typically schema v1 (just
`status` and `run_id`). The data we care most about for introspection isn't being
collected.

**No cost tracking.** We run models of varying cost (opus, sonnet, haiku, composer)
but have no per-run token counts. This makes it impossible to evaluate whether model
tier selection is calibrated correctly or to estimate costs over a plan's lifetime.

# Goals

- Restructure runs into per-task directories:
  `runs/TASK-1234/info-<timestamp>.json`, `summary-<timestamp>.log`,
  `output-<timestamp>.log`
- Stream executor output into `output-<timestamp>.log` in real-time (line-by-line)
  so it can be `tail -f`'d during execution
- Support multiple runs per task naturally (each retry gets a new timestamped triple)
- Populate `files_changed` reliably (via git diff, not executor self-report)
- Add `token_usage` field to run metadata (input tokens, output tokens, model) when
  the executor can provide it
- Provide `onward show --runs TASK-*` to display run history with durations, outcomes,
  and token counts

# Non-goals

- Real-time web dashboard (FUTURE_ROADMAP.md item)
- Cost estimation / dollar amounts (requires pricing tables; deferred)
- Changing the executor protocol for external (subprocess) executors — they can
  opt into the new schema but aren't required to
- Retroactive migration of existing flat run files (they stay; new runs use folders)

# End state

- [ ] New runs create `runs/TASK-*/` directories with three files per run attempt
- [ ] `output-*.log` is written to continuously during execution (tail-able)
- [ ] `info-*.json` includes `files_changed` populated from `git diff` and
  `token_usage` when available
- [ ] `onward show TASK-*` displays run history with timestamps, duration, model,
  outcome, and token usage
- [ ] `onward report` can show aggregate stats (total runs, pass rate, total tokens)
  when `--verbose` is passed
- [ ] Existing flat run files continue to be readable (backward compat)
- [ ] `summary-*.log` contains the post-hoc log (hook outputs, error messages) —
  same content as today's `.log` file

# Context

**Current run record flow** (`execution.py`):
1. `_prepare_task_run` creates `RUN-<ts>-<task>.json` with `status: running`
2. `_register_active_run` writes to `ongoing.json`
3. `_run_hooked_executor_batch` runs executor, collects output into `log_sections`
4. After completion: writes `run_log` (all sections joined), updates `run_json`

**BuiltinExecutor** (`executor_builtin.py`):
- Spawns subprocess, tees stdout/stderr to terminal via threads
- Collects into `stdout_chunks` / `stderr_chunks` lists
- Returns `ExecutorResult` with combined output string

The tee threads already have line-by-line access to the output stream. The key
change is to also write each line to the `output-*.log` file as it arrives, rather
than buffering everything until completion.

**Token usage availability:**
- Claude CLI (`claude -p ...`): outputs a JSON summary line at the end of execution
  that includes `input_tokens` and `output_tokens` when run with `--output-format json`
  or by parsing the final summary. The exact format depends on CLI version. The
  `--verbose` flag may expose token counts. Needs empirical testing.
- Cursor CLI: token usage may not be directly available from the CLI. This is a
  best-effort field.
- `onward-exec` (subprocess protocol): could optionally include `token_usage` in the
  `onward_task_result` ack JSON.

# Proposed approach

## Phase 1: Directory restructure

### 1a. Run directory layout

New layout:

```
.onward/runs/
├── TASK-020/
│   ├── info-2026-03-21T00-30-00Z.json
│   ├── summary-2026-03-21T00-30-00Z.log
│   └── output-2026-03-21T00-30-00Z.log
│   ├── info-2026-03-21T01-15-00Z.json     # retry
│   ├── summary-2026-03-21T01-15-00Z.log
│   └── output-2026-03-21T01-15-00Z.log
├── TASK-021/
│   └── ...
├── RUN-2026-03-20T22-27-57Z-TASK-060.json  # legacy (untouched)
└── RUN-2026-03-20T22-27-57Z-TASK-060.log   # legacy (untouched)
```

The `info-*.json` replaces the old `RUN-*.json`. The `summary-*.log` replaces the
old `RUN-*.log`. The `output-*.log` is new: the raw executor stdout/stderr stream.

### 1b. Update `_prepare_task_run`

Change `run_json` and `run_log` paths:

```python
task_dir = root / ".onward/runs" / task_id
task_dir.mkdir(parents=True, exist_ok=True)
ts = run_timestamp()
run_json = task_dir / f"info-{ts}.json"
run_log  = task_dir / f"summary-{ts}.log"
output_log = task_dir / f"output-{ts}.log"
```

Add `output_log` to the `PreparedTaskRun` dataclass.

### 1c. Backward-compatible run queries

Update `collect_runs_for_target` and `latest_run_for` to check both:
- New path: `runs/TASK-*/info-*.json`
- Legacy path: `runs/RUN-*-TASK-*.json`

Merge results, sort by `started_at`, return unified list.

### 1d. Update `run_id` format

Keep `RUN-<timestamp>-<task-id>` as the logical ID (it's referenced in ongoing.json,
ack payloads, etc.). The file paths change but the ID stays the same.

## Phase 2: Live output streaming

### 2a. Streaming tee to file

In `BuiltinExecutor.execute_task`, the `_tee_stream` function already reads
line-by-line from the subprocess pipe. Add a file handle parameter:

```python
def _tee_stream(pipe, tee_to: TextIO, buffer: list[str], file_out: TextIO | None = None):
    try:
        for line in iter(pipe.readline, ""):
            buffer.append(line)
            tee_to.write(line)
            tee_to.flush()
            if file_out is not None:
                file_out.write(line)
                file_out.flush()
    finally:
        pipe.close()
```

Open the `output-*.log` file before spawning the subprocess, pass the handle to
both stdout and stderr tee threads (or use a shared lock for interleaved writes).

### 2b. SubprocessExecutor streaming

The `SubprocessExecutor` uses `capture_output=True` (blocking). For streaming, switch
to `Popen` with piped stdout/stderr and tee threads, matching `BuiltinExecutor`'s
approach. This is a larger change but aligns the two executors.

Alternatively, keep `SubprocessExecutor` non-streaming for now (write output to
`output-*.log` at completion) and note this as a follow-up. The builtin executor
is the primary path.

### 2c. Output log as the primary run artifact

The `output-*.log` is the raw stream — everything the AI said and did. The
`summary-*.log` remains the structured log (hook results, error messages, the
post-processed output). Users `tail -f` the output log; `onward show` reads the
summary log.

## Phase 3: Reliable `files_changed`

### 3a. Git diff after task completion

Instead of relying on the executor to self-report `files_changed`, compute it from
git after the task completes (and after `post_task_shell` hooks, which typically
commit):

```python
def compute_files_changed(root: Path, before_sha: str) -> list[str]:
    """Diff HEAD against the pre-task commit SHA to get changed files."""
    result = subprocess.run(
        ["git", "diff", "--name-only", before_sha, "HEAD"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
```

Before the executor runs, capture `git rev-parse HEAD` as `before_sha`. After hooks
complete, compute the diff. Store in `info-*.json` as `files_changed`.

### 3b. Fallback: staged + unstaged diff

If the workspace doesn't auto-commit (no `post_task_shell` git hook), fall back to
`git diff --name-only` (unstaged) + `git diff --cached --name-only` (staged).

## Phase 4: Token usage tracking

### 4a. Schema extension

Add to `info-*.json`:

```json
{
  "token_usage": {
    "input_tokens": 12345,
    "output_tokens": 6789,
    "total_tokens": 19134,
    "model": "claude-sonnet-4-20250514"
  }
}
```

Field is nullable — `"token_usage": null` when not available.

### 4b. Claude CLI token extraction

Claude CLI with `--output-format json` emits structured output including token
counts. However, this changes the output format (no longer plain text streaming).

Alternative: Claude CLI prints a cost/usage summary line to stderr at the end. Parse
it with a regex. This is fragile but doesn't change the invocation.

Best approach: add `--output-format stream-json` if available (NDJSON with a final
`result` message containing usage). Parse the final line. Fall back to null if the
format isn't recognized. This needs empirical testing against the current Claude
CLI version.

### 4c. Ack-based token reporting

Extend `onward_task_result` schema v3 with optional `token_usage`:

```json
{
  "onward_task_result": {
    "schema_version": 3,
    "status": "completed",
    "token_usage": { "input_tokens": 12345, "output_tokens": 6789 }
  }
}
```

Executors that can track usage report it in the ack. Onward stores it in
`info-*.json`. This is the cleanest long-term path and works for all executor types.

### 4d. Aggregation

Add `token_usage` to `collect_runs_for_target` output. `onward show --runs TASK-*`
displays per-run tokens. `onward report --verbose` sums tokens across all runs in
a plan.

## Phase 5: Reporting improvements

### 5a. `onward show TASK-* --runs`

Display run history table:

```
Runs for TASK-020 (2 runs):
  #1  2026-03-21T00:30:00Z  completed  2m13s  composer-2  1.2k/4.5k tokens  3 files
  #2  2026-03-21T01:15:00Z  failed     0m45s  composer-2  0.8k/1.2k tokens  0 files
```

### 5b. `onward report --verbose`

Add an optional stats section at the bottom:

```
[Run stats]
  Total runs: 14 (12 completed, 2 failed)
  Total tokens: 45.2k input / 123.4k output
  Pass rate: 85.7%
```

### 5c. Per-task `files_changed` in show output

```
Files changed (TASK-020, run #1):
  M src/onward/execution.py
  A src/onward/claiming.py
  M tests/test_execution.py
```

# Key artifacts

- `src/onward/execution.py` — restructured run paths, git-based `files_changed`,
  `before_sha` capture
- `src/onward/executor_builtin.py` — `_tee_stream` with file output, output log handle
- `src/onward/executor.py` — `ExecutorResult` extended with optional `token_usage`
- `src/onward/executor_ack.py` — schema v3 with `token_usage` field
- `src/onward/cli_commands.py` — `cmd_show` run history, `cmd_report` verbose stats
- `src/onward/util.py` — helper for git diff computation
- `docs/WORK_HANDOFF.md` — document new run directory layout and ack schema v3

# Acceptance criteria

- New task run creates `runs/TASK-*/info-*.json`, `summary-*.log`, `output-*.log`
- `output-*.log` is written to during execution (verifiable via `tail -f` in another
  terminal while a task runs)
- `files_changed` is populated from git diff (not empty list) for tasks that modify
  files and have a `post_task_shell` git commit hook
- Legacy `RUN-*.json` / `RUN-*.log` files are still readable by `onward show`
- `onward show TASK-* --runs` displays run history with timestamps and outcomes
- `token_usage` is populated when the executor provides it (nullable when not);
  no crash or error when unavailable
- All existing tests pass; new tests cover directory layout, backward compat,
  streaming write, git diff computation, and token parsing
- A retried task has multiple run triples in its directory, each independently
  readable

# Notes

- Token tracking is explicitly best-effort. Claude CLI's output format may change
  between versions. The system should degrade gracefully (null token_usage) rather
  than fail.
- The output log can get large (full AI conversation). Consider adding a
  `work.max_output_log_bytes` config key to truncate or rotate, but this is a
  follow-up concern.
- The combination of `files_changed` (from git diff), `token_usage`, `model`, and
  `duration` gives us the data needed for model selection tuning — e.g., "sonnet
  takes 40% fewer tokens than opus for small tasks with similar pass rates."
- The `onward-exec` subprocess executor could be updated separately to stream to
  the output file, or we could deprecate it in favor of builtin. Either way, the
  builtin executor is the priority path.
