---
id: "TASK-049"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-012"
project: ""
title: "Use index.yaml for fast reads"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:08Z"
updated_at: "2026-03-20T16:01:08Z"
---

# Context

Onward regenerates `index.yaml` on every write operation, but read commands (`list`, `next`, `ready`, `report`, `tree`) ignore it and do a full filesystem scan via `collect_artifacts()`. For workspaces with many plans, this is slow. This task makes read-heavy commands use `index.yaml` as a fast path when available, falling back to full scan when the index is stale or missing.

# Scope

- Add `index_version` counter to `index.yaml` (incremented on each regeneration)
- Add `load_index(root) -> dict | None` function in `artifacts.py` that reads and parses `index.yaml`
- Add `index_is_fresh(root, index) -> bool` that checks `index_version` and `generated_at` against a staleness threshold (e.g., file mtime comparison)
- Add `list_from_index(index, type_filter, status_filter, project_filter)` that returns rows from the index without touching artifact files
- Use `list_from_index` in `cmd_list`, `cmd_next`, `cmd_ready` (if it exists) for the common case
- Keep full scan as fallback: if index is missing, stale, or load fails, fall back to `collect_artifacts`
- Update `regenerate_indexes` to include `index_version` counter
- Add tests for index-based reads, staleness detection, fallback behavior

# Out of scope

- Incremental index updates (always full regeneration for now)
- Index for run records (only plans/chunks/tasks)
- Binary/sqlite index format
- Concurrent access locking

# Files to inspect

- `src/onward/artifacts.py` — `regenerate_indexes()` (line ~311), `collect_artifacts()`, `select_next_artifact()`
- `src/onward/cli_commands.py` — `cmd_list()`, `cmd_next()`, `cmd_ready()`, `cmd_report()`, `cmd_tree()`
- `.onward/plans/index.yaml` — current format to extend

# Implementation notes

- The index currently stores: `generated_at`, `plans`, `chunks`, `tasks`, `runs`. Each entry has `id`, `title`, `status`, `path` (plus `plan`/`chunk` for hierarchical types). This is enough for `list` and basic filtering.
- `index_version` should be a monotonically increasing integer. Store it at the top level of `index.yaml`. Initialize at 1 on first regeneration.
- Staleness check: compare the `generated_at` timestamp in the index against the newest `updated_at` across artifact files. Simpler alternative: compare the index file's mtime against the newest artifact file's mtime. The mtime approach is faster (no file reads).
- `list_from_index` returns a lightweight representation (dicts with id, type, status, title, path, plan, chunk). This avoids parsing frontmatter of every artifact file.
- Commands that need the full artifact body (`cmd_show`, `cmd_work`) should NOT use the index — they need the full file content.
- `cmd_next` and `cmd_ready` need dependency resolution which requires `depends_on` data. The index doesn't currently include this. Options: (a) add `depends_on` to the index, (b) do a full scan for these commands. Recommendation: add `depends_on` to the task entries in the index.
- `cmd_report` calls `select_next_artifact` which does dependency resolution — this needs the full artifact data. Consider keeping `cmd_report` on full scan, or enrich the index with enough data.

# Acceptance criteria

- `index.yaml` includes `index_version` counter
- `onward list` reads from index when fresh (no full artifact scan)
- Stale or missing index falls back to full scan transparently
- `index_version` increments on each `regenerate_indexes` call
- Commands that need full artifact data still do full scan
- Tests cover: index read, staleness detection, fallback, version increment

# Handoff notes

- This is a performance optimization — behavior should be identical whether reading from index or full scan.
- The biggest complexity is deciding which commands can use the index and which need full scan. Start conservative: only `cmd_list` with simple filters uses the index. Expand later.
- Adding `depends_on` to the index is the key enabler for `cmd_next` and `cmd_ready` to use it. This increases index size but keeps reads fast.
- Future enhancement: incremental index updates (only rewrite changed entries) for large workspaces.
