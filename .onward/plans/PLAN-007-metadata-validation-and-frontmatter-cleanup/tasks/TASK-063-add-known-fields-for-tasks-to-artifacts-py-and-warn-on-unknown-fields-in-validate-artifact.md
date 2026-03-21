---
id: "TASK-063"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-017"
project: ""
title: "Add KNOWN_FIELDS for tasks to artifacts.py and warn on unknown fields in validate_artifact"
status: "completed"
description: "In `src/onward/artifacts.py`, add a new module-level dict `KNOWN_FIELDS` (parallel to the existing `REQUIRED_FIELDS`) that maps artifact type to a frozenset of allowed frontmatter keys. Define at least the `\"task\"` entry — it should include all expected task keys (`id`, `type`, `plan`, `chunk`, `project`, `title`, `status`, `description`, `human`, `model`, `executor`, `depends_on`, `effort`, `created_at`, `updated_at`) but must NOT include `files` or `acceptance`.\n\nExtend `validate_artifact()` to: after the required-fields check, look up `KNOWN_FIELDS.get(artifact_type)`. If a known-fields set exists, iterate over the actual frontmatter keys; for any key not in the known set, append a warning string of the form `\"{path}: unknown task field '{key}'\"` (use `\"unknown {type} field\"` pattern) to the issues list. Return these as issues (doctor prints them as issues, so the output will surface them).\n\nLeave `KNOWN_FIELDS` for `\"plan\"` and `\"chunk\"` either absent or permissive (empty set or omit) — only task fields are tightened in this chunk."
human: false
model: "sonnet"
executor: "onward-exec"
depends_on: []
files:
- "src/onward/artifacts.py"
acceptance:
- "Running `onward doctor` on a workspace that contains a task file with `files:` in frontmatter produces a line containing `unknown task field 'files'`"
- "Running `onward doctor` on a workspace that contains a task file with `acceptance:` in frontmatter produces a line containing `unknown task field 'acceptance'`"
- "Running `onward doctor` on a task without those keys produces no extra issues"
- "REQUIRED_FIELDS is unchanged; validate_artifact still raises required-field issues as before"
created_at: "2026-03-21T20:25:46Z"
updated_at: "2026-03-21T21:06:30Z"
effort: "s"
run_count: 1
last_run_status: "completed"
---

# Context

In `src/onward/artifacts.py`, add a new module-level dict `KNOWN_FIELDS` (parallel to the existing `REQUIRED_FIELDS`) that maps artifact type to a frozenset of allowed frontmatter keys. Define at least the `"task"` entry — it should include all expected task keys (`id`, `type`, `plan`, `chunk`, `project`, `title`, `status`, `description`, `human`, `model`, `executor`, `depends_on`, `effort`, `created_at`, `updated_at`) but must NOT include `files` or `acceptance`.

Extend `validate_artifact()` to: after the required-fields check, look up `KNOWN_FIELDS.get(artifact_type)`. If a known-fields set exists, iterate over the actual frontmatter keys; for any key not in the known set, append a warning string of the form `"{path}: unknown task field '{key}'"` (use `"unknown {type} field"` pattern) to the issues list. Return these as issues (doctor prints them as issues, so the output will surface them).

Leave `KNOWN_FIELDS` for `"plan"` and `"chunk"` either absent or permissive (empty set or omit) — only task fields are tightened in this chunk.

# Scope

- In `src/onward/artifacts.py`, add a new module-level dict `KNOWN_FIELDS` (parallel to the existing `REQUIRED_FIELDS`) that maps artifact type to a frozenset of allowed frontmatter keys. Define at least the `"task"` entry — it should include all expected task keys (`id`, `type`, `plan`, `chunk`, `project`, `title`, `status`, `description`, `human`, `model`, `executor`, `depends_on`, `effort`, `created_at`, `updated_at`) but must NOT include `files` or `acceptance`.

Extend `validate_artifact()` to: after the required-fields check, look up `KNOWN_FIELDS.get(artifact_type)`. If a known-fields set exists, iterate over the actual frontmatter keys; for any key not in the known set, append a warning string of the form `"{path}: unknown task field '{key}'"` (use `"unknown {type} field"` pattern) to the issues list. Return these as issues (doctor prints them as issues, so the output will surface them).

Leave `KNOWN_FIELDS` for `"plan"` and `"chunk"` either absent or permissive (empty set or omit) — only task fields are tightened in this chunk.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/artifacts.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- Running `onward doctor` on a workspace that contains a task file with `files:` in frontmatter produces a line containing `unknown task field 'files'`
- Running `onward doctor` on a workspace that contains a task file with `acceptance:` in frontmatter produces a line containing `unknown task field 'acceptance'`
- Running `onward doctor` on a task without those keys produces no extra issues
- REQUIRED_FIELDS is unchanged; validate_artifact still raises required-field issues as before

# Handoff notes
