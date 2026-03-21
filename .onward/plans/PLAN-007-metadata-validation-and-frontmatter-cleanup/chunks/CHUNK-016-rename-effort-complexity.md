---
id: "CHUNK-016"
type: "chunk"
plan: "PLAN-007"
project: ""
title: "Rename effort → complexity"
status: "completed"
description: "Rename normalize_effort → normalize_complexity in util.py; accept only low|medium|high (drop xs/s/m/l/xl). Update config.py (_EFFORT_TIER_VALUES, resolve_model_for_task) to read the complexity key with a fallback to effort for backward compat. Update cli.py --effort flag → --complexity on new task and batch. Update all call sites in cli_commands.py, split.py, artifacts.py (summarize_effort_remaining → summarize_complexity_remaining, metadata key reads). Update scaffold.py templates and prompts. Update executor_payload.py. Update docs. Update all affected tests. Keep a single compat fallback reading the old effort key where documented."
priority: "high"
model: "sonnet"
depends_on:
- "CHUNK-015"
created_at: "2026-03-21T20:18:55Z"
updated_at: "2026-03-21T21:01:10Z"
---

# Summary

Rename normalize_effort → normalize_complexity in util.py; accept only low|medium|high (drop xs/s/m/l/xl). Update config.py (_EFFORT_TIER_VALUES, resolve_model_for_task) to read the complexity key with a fallback to effort for backward compat. Update cli.py --effort flag → --complexity on new task and batch. Update all call sites in cli_commands.py, split.py, artifacts.py (summarize_effort_remaining → summarize_complexity_remaining, metadata key reads). Update scaffold.py templates and prompts. Update executor_payload.py. Update docs. Update all affected tests. Keep a single compat fallback reading the old effort key where documented.

# Scope

- Rename normalize_effort → normalize_complexity in util.py; accept only low|medium|high (drop xs/s/m/l/xl). Update config.py (_EFFORT_TIER_VALUES, resolve_model_for_task) to read the complexity key with a fallback to effort for backward compat. Update cli.py --effort flag → --complexity on new task and batch. Update all call sites in cli_commands.py, split.py, artifacts.py (summarize_effort_remaining → summarize_complexity_remaining, metadata key reads). Update scaffold.py templates and prompts. Update executor_payload.py. Update docs. Update all affected tests. Keep a single compat fallback reading the old effort key where documented.

# Out of scope

- None specified.

# Dependencies

- CHUNK-015

# Expected files/systems involved

**Must touch:**
- `src/onward/util.py`
- `src/onward/config.py`
- `src/onward/split.py`
- `src/onward/cli.py`
- `src/onward/cli_commands.py`
- `src/onward/artifacts.py`
- `src/onward/scaffold.py`
- `src/onward/executor_payload.py`

**Likely:**
- `tests/test_cli_scale.py`
- `tests/test_architecture_seams.py`
- `tests/test_run_record_io.py`
- `tests/test_cli_report_md.py`
- `tests/test_cli_split.py`
- `docs/CAPABILITIES.md`
- `docs/WORK_HANDOFF.md`
- `docs/FUTURE_ROADMAP.md`
- `docs/AI_OPERATOR.md`

**Deferred / out of scope for this chunk:**
- `.onward/ task files with effort: key (user data — doctor warns, no code change)`

# Completion criteria

- normalize_complexity('low'|'medium'|'high') returns the value unchanged; normalize_complexity('xl') returns ''
- resolve_model_for_task reads complexity key and falls back to effort key for tasks that still use the old name
- onward new task --complexity high produces frontmatter with complexity: high and no effort key
- onward new task --effort high is rejected or aliased with a deprecation warning (flag removed or aliased)
- Zero grep matches for normalize_effort or --effort in source (excluding the compat fallback comment)
- All existing tests pass with updated assertions

# Notes
