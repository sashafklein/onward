---
id: "TASK-054"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-016"
project: ""
title: "config.py: update resolve_model_for_task to read complexity with effort fallback"
status: "open"
description: "In `src/onward/config.py`, update `resolve_model_for_task`:\n\n1. Change resolution step 2 to read `task_metadata.get('complexity')` first; if absent or invalid, fall back to `task_metadata.get('effort')` for backward compatibility (tasks on disk may still use the old key). Both must map through `_EFFORT_TIER_VALUES` (which already contains `{'high', 'medium', 'low'}` — no change needed there).\n2. Update the docstring: rename references from `task_metadata[\"effort\"]` to `task_metadata[\"complexity\"]` and document the `effort` fallback with a comment like `# compat: fall back to legacy 'effort' key`.\n\nThe `_EFFORT_TIER_VALUES` frozenset at line 269 already contains `{\"high\", \"medium\", \"low\"}` and does not need to change.\n\nContrect change — replace:\n```python\nraw_effort = task_metadata.get(\"effort\")\nif raw_effort is not None:\n    e = str(raw_effort).strip().lower()\n    if e in _EFFORT_TIER_VALUES:\n        return resolve_model_for_tier(config, e)\n```\nWith:\n```python\nraw_complexity = task_metadata.get(\"complexity\")\nif raw_complexity is None:  # compat: fall back to legacy 'effort' key\n    raw_complexity = task_metadata.get(\"effort\")\nif raw_complexity is not None:\n    e = str(raw_complexity).strip().lower()\n    if e in _EFFORT_TIER_VALUES:\n        return resolve_model_for_tier(config, e)\n```"
human: false
model: "haiku"
executor: "onward-exec"
depends_on:
- "TASK-053"
files:
- "src/onward/config.py"
acceptance:
- "resolve_model_for_task(cfg, {'complexity': 'low'}) resolves correctly"
- "resolve_model_for_task(cfg, {'effort': 'low'}) still resolves correctly (compat fallback)"
- "resolve_model_for_task(cfg, {'complexity': 'high', 'effort': 'low'}) uses complexity (high) not effort (low)"
- "resolve_model_for_task(cfg, {'complexity': 'xl'}) falls back to default tier (xl is not a valid complexity)"
- "Docstring updated to reference complexity key and document effort fallback"
created_at: "2026-03-21T20:23:52Z"
updated_at: "2026-03-21T20:23:52Z"
effort: "xs"
---

# Context

In `src/onward/config.py`, update `resolve_model_for_task`:

1. Change resolution step 2 to read `task_metadata.get('complexity')` first; if absent or invalid, fall back to `task_metadata.get('effort')` for backward compatibility (tasks on disk may still use the old key). Both must map through `_EFFORT_TIER_VALUES` (which already contains `{'high', 'medium', 'low'}` — no change needed there).
2. Update the docstring: rename references from `task_metadata["effort"]` to `task_metadata["complexity"]` and document the `effort` fallback with a comment like `# compat: fall back to legacy 'effort' key`.

The `_EFFORT_TIER_VALUES` frozenset at line 269 already contains `{"high", "medium", "low"}` and does not need to change.

Contrect change — replace:
```python
raw_effort = task_metadata.get("effort")
if raw_effort is not None:
    e = str(raw_effort).strip().lower()
    if e in _EFFORT_TIER_VALUES:
        return resolve_model_for_tier(config, e)
```
With:
```python
raw_complexity = task_metadata.get("complexity")
if raw_complexity is None:  # compat: fall back to legacy 'effort' key
    raw_complexity = task_metadata.get("effort")
if raw_complexity is not None:
    e = str(raw_complexity).strip().lower()
    if e in _EFFORT_TIER_VALUES:
        return resolve_model_for_tier(config, e)
```

# Scope

- In `src/onward/config.py`, update `resolve_model_for_task`:

1. Change resolution step 2 to read `task_metadata.get('complexity')` first; if absent or invalid, fall back to `task_metadata.get('effort')` for backward compatibility (tasks on disk may still use the old key). Both must map through `_EFFORT_TIER_VALUES` (which already contains `{'high', 'medium', 'low'}` — no change needed there).
2. Update the docstring: rename references from `task_metadata["effort"]` to `task_metadata["complexity"]` and document the `effort` fallback with a comment like `# compat: fall back to legacy 'effort' key`.

The `_EFFORT_TIER_VALUES` frozenset at line 269 already contains `{"high", "medium", "low"}` and does not need to change.

Contrect change — replace:
```python
raw_effort = task_metadata.get("effort")
if raw_effort is not None:
    e = str(raw_effort).strip().lower()
    if e in _EFFORT_TIER_VALUES:
        return resolve_model_for_tier(config, e)
```
With:
```python
raw_complexity = task_metadata.get("complexity")
if raw_complexity is None:  # compat: fall back to legacy 'effort' key
    raw_complexity = task_metadata.get("effort")
if raw_complexity is not None:
    e = str(raw_complexity).strip().lower()
    if e in _EFFORT_TIER_VALUES:
        return resolve_model_for_tier(config, e)
```

# Out of scope

- None specified.

# Files to inspect

- `src/onward/config.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- resolve_model_for_task(cfg, {'complexity': 'low'}) resolves correctly
- resolve_model_for_task(cfg, {'effort': 'low'}) still resolves correctly (compat fallback)
- resolve_model_for_task(cfg, {'complexity': 'high', 'effort': 'low'}) uses complexity (high) not effort (low)
- resolve_model_for_task(cfg, {'complexity': 'xl'}) falls back to default tier (xl is not a valid complexity)
- Docstring updated to reference complexity key and document effort fallback

# Handoff notes
