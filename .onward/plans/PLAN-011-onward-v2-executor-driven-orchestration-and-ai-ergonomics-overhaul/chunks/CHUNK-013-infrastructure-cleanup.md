---
id: "CHUNK-013"
type: "chunk"
plan: "PLAN-011"
project: ""
title: "Infrastructure cleanup"
status: "open"
description: "Replace custom YAML parser with PyYAML, move model resolution to executor, clean up hooks, create FUTURE_ROADMAP."
priority: "low"
model: "sonnet-latest"
estimated_files: 18
depends_on:
  - "CHUNK-008"
created_at: "2026-03-20T15:52:26Z"
updated_at: "2026-03-20T15:52:26Z"
---

# Summary

Technical debt cleanup: replace the hand-rolled YAML parser with PyYAML, remove model alias resolution from Onward core (executor handles it), simplify the hook system, and create a FUTURE_ROADMAP.md parking lot for deferred work.

# Scope

- Add `pyyaml` dependency, replace `parse_simple_yaml`/`dump_simple_yaml` with PyYAML
- Remove `MODEL_FAMILIES` and `resolve_model_alias` from config.py (executor-side)
- Remove unused `pre_task_markdown` hook (null by default, never used)
- Add `pre_chunk_shell` hook for symmetry
- Document the remaining hooks clearly
- Create `docs/FUTURE_ROADMAP.md` with deferred items:
  - Parallel task execution within chunks
  - Incremental index regeneration
  - Daemon mode
  - Worktree-per-chunk
  - Cross-workspace dependencies
  - Web dashboard

# Out of scope

- Actually implementing any FUTURE_ROADMAP items
- Breaking changes to hook execution order

# Dependencies

- CHUNK-008 (executor must handle model resolution before we remove it)

# Expected files/systems involved

- `pyproject.toml` — add pyyaml dependency
- `src/onward/util.py` — replace YAML parser
- `src/onward/config.py` — remove model resolution
- `src/onward/execution.py` — stop calling resolve_model_alias
- `src/onward/scaffold.py` — updated hook defaults
- `docs/WORK_HANDOFF.md` — updated hook docs
- `docs/FUTURE_ROADMAP.md` — new
- `tests/test_frontmatter_parser.py` — updated for PyYAML

# Completion criteria

- [ ] PyYAML is the YAML parser; custom parser removed
- [ ] Model alias resolution removed from Onward; executor handles it
- [ ] Hook system simplified and documented
- [ ] `docs/FUTURE_ROADMAP.md` exists with deferred items
- [ ] All tests pass
