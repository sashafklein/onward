---
id: "TASK-012"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-005"
project: ""
title: "Replace private cross-module calls with stable interfaces"
status: "completed"
description: "Reduce underscore-internal imports and hardcoded wiring"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:22Z"
updated_at: "2026-03-20T01:06:27Z"
---

# Context

PLAN-010 phase 3: modules call **`_private`** helpers across package boundaries today; extensions and refactors break silently. Introduce **stable public APIs** (documented functions, no leading underscore) for cross-module use.

# Scope

- Inventory `_`-prefixed imports between `onward.*` modules.
- For each seam, expose a small public API (or consolidate into owning module).
- Update call sites; deprecate or remove duplicate private entrypoints.

# Out of scope

- Third-party plugin system; changing external CLI contract.

# Files to inspect

- All `src/onward/*.py` import graphs; focus on `cli.py` → others after TASK-011.

# Implementation notes

- Prefer names that match domain language (`load_workspace`, `run_task`, etc.). Keep surface minimal.

# Acceptance criteria

- No remaining cross-module `_foo` imports for package-internal use (tests may still target internals if isolated).
- TASK-013 can assert module boundaries.

# Handoff notes

- Renamed or aliased cross-module `onward.*` entrypoints so no package-internal import uses a leading-underscore symbol from another `onward` module.
- `util`: public aliases (`clean_string`, `parse_simple_yaml`, `now_iso`, `dump_run_json_record`, …) point at existing `_`-prefixed implementations.
- `config`: `load_workspace_config`, `is_ralph_enabled`, `model_setting`, `resolve_model_alias`, `load_artifact_template`, `work_sequential_by_default`.
- `artifacts`, `execution`, `split`, `scaffold`: former `_foo` APIs used across modules are now public `foo` names; truly internal helpers stay `_`-prefixed within the owning module.
- Tests updated to import public names where they previously reached for `_find_by_id` / util helpers.
- Full `pytest tests/` passes (Python 3.11).
