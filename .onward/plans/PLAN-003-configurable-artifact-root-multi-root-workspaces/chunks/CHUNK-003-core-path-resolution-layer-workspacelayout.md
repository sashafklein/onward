---
id: "CHUNK-003"
type: "chunk"
plan: "PLAN-003"
project: ""
title: "Core path resolution layer (WorkspaceLayout)"
status: "in_progress"
description: "Introduce WorkspaceLayout dataclass and config keys for root/roots path resolution"
priority: "high"
effort: "l"
model: "claude-opus-4-5"
created_at: "2026-03-21T15:46:40Z"
updated_at: "2026-03-21T16:17:08Z"
---

# Summary

Build the foundational `WorkspaceLayout` class and config parsing that everything else depends on. After this chunk, the codebase has a single source of truth for "where do artifact directories live?" but nothing is wired up yet.

# Scope

- Add `root`, `roots`, `default_project` to `CONFIG_TOP_LEVEL_KEYS` and validation
- Create `WorkspaceLayout` dataclass in `config.py` (or a new `layout.py`) with methods: `artifact_root(project)`, `plans_dir(project)`, `runs_dir(project)`, `reviews_dir(project)`, `templates_dir(project)`, `prompts_dir(project)`, `hooks_dir(project)`, `notes_dir(project)`, `sync_dir(project)`, `ongoing_path(project)`, `index_path(project)`, `recent_path(project)`, `archive_dir(project)`
- `WorkspaceLayout.from_config(root, config)` constructor that reads `root`/`roots`/`default_project` from config
- Default behavior when neither `root` nor `roots` is set: `.onward/` (backward compatible)
- Validation: `root` and `roots` mutually exclusive; `default_project` must match a `roots` key
- `resolve_project(project_arg, layout)` helper that resolves `--project` against the layout (returns project key or errors)
- `all_project_keys(layout)` helper for iteration
- Unit tests for `WorkspaceLayout` in isolation (various config shapes)

# Out of scope

- Actually replacing `.onward/` references in other files (that's CHUNK-005)
- Scaffold/init changes (CHUNK-004)
- CLI argument changes (CHUNK-006)
- Sync changes (CHUNK-007)

# Dependencies

None — this is the foundation chunk.

# Expected files/systems involved

- `src/onward/config.py` — new class, new config keys, updated validation
- `tests/test_config.py` or new `tests/test_layout.py` — unit tests for WorkspaceLayout

# Completion criteria

- [ ] `WorkspaceLayout.from_config(root, {})` returns layout with `.onward/` as default root
- [ ] `WorkspaceLayout.from_config(root, {"root": "nb"})` returns layout with `nb/` as root
- [ ] `WorkspaceLayout.from_config(root, {"roots": {"a": "./a", "b": "./b"}})` returns multi-root layout
- [ ] Calling `layout.plans_dir()` in single-root mode returns `<root>/nb/plans` (or `.onward/plans`)
- [ ] Calling `layout.plans_dir("a")` in multi-root mode returns `<root>/a/plans`
- [ ] Calling `layout.plans_dir()` in multi-root mode without default_project raises ValueError
- [ ] `validate_config_contract_issues` catches `root` + `roots` together
- [ ] `validate_config_contract_issues` catches invalid `default_project` (not in roots keys)
- [ ] All existing tests pass (no behavior change yet)
