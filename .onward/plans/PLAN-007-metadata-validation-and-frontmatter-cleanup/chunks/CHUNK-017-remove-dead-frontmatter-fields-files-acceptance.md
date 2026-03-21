---
id: "CHUNK-017"
type: "chunk"
plan: "PLAN-007"
project: ""
title: "Remove dead frontmatter fields (files, acceptance)"
status: "in_progress"
description: "Stop emitting files and acceptance keys in task frontmatter. In split.py, remove those keys from the metadata dict built for each task (they are already rendered into the markdown body). In cli_commands.py cmd_batch(), same removal. Do not include files or acceptance in KNOWN_FIELDS for tasks in artifacts.py (so doctor warns on existing tasks that still carry them). Update tests that assert on frontmatter content to not expect these keys."
priority: "medium"
model: "sonnet"
depends_on:
- "CHUNK-016"
created_at: "2026-03-21T20:18:55Z"
updated_at: "2026-03-21T21:01:11Z"
---

# Summary

Stop emitting files and acceptance keys in task frontmatter. In split.py, remove those keys from the metadata dict built for each task (they are already rendered into the markdown body). In cli_commands.py cmd_batch(), same removal. Do not include files or acceptance in KNOWN_FIELDS for tasks in artifacts.py (so doctor warns on existing tasks that still carry them). Update tests that assert on frontmatter content to not expect these keys.

# Scope

- Stop emitting files and acceptance keys in task frontmatter. In split.py, remove those keys from the metadata dict built for each task (they are already rendered into the markdown body). In cli_commands.py cmd_batch(), same removal. Do not include files or acceptance in KNOWN_FIELDS for tasks in artifacts.py (so doctor warns on existing tasks that still carry them). Update tests that assert on frontmatter content to not expect these keys.

# Out of scope

- None specified.

# Dependencies

- CHUNK-016

# Expected files/systems involved

**Must touch:**
- `src/onward/split.py`
- `src/onward/cli_commands.py`
- `src/onward/artifacts.py`

**Likely:**
- `tests/test_cli_split.py`
- `tests/test_cli_artifacts.py`
- `tests/test_cli_lifecycle.py`
- `tests/test_onboarding_simulation.py`

**Deferred / out of scope for this chunk:**
- `.onward/ existing task files with files:/acceptance: in frontmatter (doctor warns; user cleans up manually)`

# Completion criteria

- A task file created by onward split or onward new task does not contain files: or acceptance: keys in its YAML frontmatter
- A task file created by onward batch does not contain files: or acceptance: keys in its YAML frontmatter
- onward doctor reports files and acceptance as unknown frontmatter fields on a task that still has them
- All existing tests pass with updated assertions

# Notes
