---
id: "TASK-088"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-026"
project: ""
title: "Add compute_files_changed helper in util.py"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: []
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:40:00Z"
---

# Context

`files_changed` in run records is currently empty because executors don't reliably
self-report it. A simple `git diff --name-only <before_sha> HEAD` after the task
commits gives an accurate list.

# Scope

- Add to `src/onward/util.py`:
  ```python
  def compute_files_changed(root: Path, before_sha: str) -> list[str]:
      """Return list of files changed between before_sha and HEAD."""
      if not before_sha:
          return []
      result = subprocess.run(
          ["git", "diff", "--name-only", before_sha, "HEAD"],
          cwd=root, capture_output=True, text=True, check=False,
      )
      if result.returncode != 0:
          return []
      return [l.strip() for l in result.stdout.splitlines() if l.strip()]
  ```
- Also add a `get_head_sha(root: Path) -> str` helper that runs `git rev-parse HEAD` and returns `""` on failure

# Out of scope

- Calling these helpers from `execution.py` (TASK-089)

# Files to inspect

- `src/onward/util.py` — existing helpers and imports

# Implementation notes

- Use `check=False` — never let a git failure crash execution
- Both helpers should silently return empty/`""` when git is unavailable

# Acceptance criteria

- [ ] `compute_files_changed(root, sha)` returns a list of relative file paths
- [ ] Returns `[]` when `before_sha` is empty string
- [ ] Returns `[]` when git command fails (non-zero exit)
- [ ] `get_head_sha(root)` returns current HEAD sha or `""` on error
- [ ] Unit tests for both helpers (use `subprocess` mock or a tmp git repo)

# Handoff notes

TASK-089 wires these helpers into the execution flow.
