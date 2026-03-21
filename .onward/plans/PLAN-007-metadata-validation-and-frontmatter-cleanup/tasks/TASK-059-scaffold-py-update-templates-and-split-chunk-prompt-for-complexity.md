---
id: "TASK-059"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-016"
project: ""
title: "scaffold.py: update templates and split-chunk prompt for complexity"
status: "completed"
description: "In `src/onward/scaffold.py`:\n\n1. **chunk.md template comment (~line 174):** Change `effort: xs|s|m|l|xl` to `complexity: low|medium|high`. The full comment becomes: `<!-- Optional. Frontmatter may include optional ``complexity: low|medium|high`` and ``estimated_files: <int>`` for chunks. -->`\n\n2. **task.md template comment (~line 204):** Change `effort: xs|s|m|l|xl` to `complexity: low|medium|high`. The full comment becomes: `<!-- Frontmatter may include optional ``complexity: low|medium|high``. -->`\n\n3. **split-chunk.md prompt (~lines 281-298):** \n   - Under `## Models and effort`, rename the section heading to `## Models and complexity`\n   - Change `**effort**: xs | s | m | l | xl — rough size (optional but preferred).` to `**complexity**: low | medium | high — rough size (optional but preferred).`\n   - In the output format description (~line 294), change `effort (string: xs|s|m|l|xl or empty string if unknown)` to `complexity (string: low|medium|high or empty string if unknown)`\n   - In the illustrative JSON example (~line 298), change `\"effort\":\"s\"` to `\"complexity\":\"medium\"`\n\n4. **executor_payload.py**: This file has no effort-related code that needs updating; no changes needed.\n\nNote: The split-plan.md prompt does not reference effort and does not need updating."
human: false
model: "haiku"
executor: "onward-exec"
depends_on: []
files:
- "src/onward/scaffold.py"
acceptance:
- "chunk.md template comment references complexity: low|medium|high"
- "task.md template comment references complexity: low|medium|high"
- "split-chunk.md prompt section heading is 'Models and complexity'"
- "split-chunk.md prompt instructs AI to output complexity: low|medium|high not effort: xs|s|m|l|xl"
- "split-chunk.md example JSON uses 'complexity' key not 'effort'"
- "Zero grep matches for 'effort: xs' in scaffold.py"
created_at: "2026-03-21T20:23:52Z"
updated_at: "2026-03-21T20:58:13Z"
effort: "s"
run_count: 1
last_run_status: "completed"
---

# Context

In `src/onward/scaffold.py`:

1. **chunk.md template comment (~line 174):** Change `effort: xs|s|m|l|xl` to `complexity: low|medium|high`. The full comment becomes: `<!-- Optional. Frontmatter may include optional ``complexity: low|medium|high`` and ``estimated_files: <int>`` for chunks. -->`

2. **task.md template comment (~line 204):** Change `effort: xs|s|m|l|xl` to `complexity: low|medium|high`. The full comment becomes: `<!-- Frontmatter may include optional ``complexity: low|medium|high``. -->`

3. **split-chunk.md prompt (~lines 281-298):** 
   - Under `## Models and effort`, rename the section heading to `## Models and complexity`
   - Change `**effort**: xs | s | m | l | xl — rough size (optional but preferred).` to `**complexity**: low | medium | high — rough size (optional but preferred).`
   - In the output format description (~line 294), change `effort (string: xs|s|m|l|xl or empty string if unknown)` to `complexity (string: low|medium|high or empty string if unknown)`
   - In the illustrative JSON example (~line 298), change `"effort":"s"` to `"complexity":"medium"`

4. **executor_payload.py**: This file has no effort-related code that needs updating; no changes needed.

Note: The split-plan.md prompt does not reference effort and does not need updating.

# Scope

- In `src/onward/scaffold.py`:

1. **chunk.md template comment (~line 174):** Change `effort: xs|s|m|l|xl` to `complexity: low|medium|high`. The full comment becomes: `<!-- Optional. Frontmatter may include optional ``complexity: low|medium|high`` and ``estimated_files: <int>`` for chunks. -->`

2. **task.md template comment (~line 204):** Change `effort: xs|s|m|l|xl` to `complexity: low|medium|high`. The full comment becomes: `<!-- Frontmatter may include optional ``complexity: low|medium|high``. -->`

3. **split-chunk.md prompt (~lines 281-298):** 
   - Under `## Models and effort`, rename the section heading to `## Models and complexity`
   - Change `**effort**: xs | s | m | l | xl — rough size (optional but preferred).` to `**complexity**: low | medium | high — rough size (optional but preferred).`
   - In the output format description (~line 294), change `effort (string: xs|s|m|l|xl or empty string if unknown)` to `complexity (string: low|medium|high or empty string if unknown)`
   - In the illustrative JSON example (~line 298), change `"effort":"s"` to `"complexity":"medium"`

4. **executor_payload.py**: This file has no effort-related code that needs updating; no changes needed.

Note: The split-plan.md prompt does not reference effort and does not need updating.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/scaffold.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- chunk.md template comment references complexity: low|medium|high
- task.md template comment references complexity: low|medium|high
- split-chunk.md prompt section heading is 'Models and complexity'
- split-chunk.md prompt instructs AI to output complexity: low|medium|high not effort: xs|s|m|l|xl
- split-chunk.md example JSON uses 'complexity' key not 'effort'
- Zero grep matches for 'effort: xs' in scaffold.py

# Handoff notes
