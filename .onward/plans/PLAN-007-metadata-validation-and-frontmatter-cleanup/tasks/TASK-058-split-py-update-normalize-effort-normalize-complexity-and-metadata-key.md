---
id: "TASK-058"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-016"
project: ""
title: "split.py: update normalize_effort → normalize_complexity and metadata key"
status: "completed"
description: "In `src/onward/split.py`:\n\n1. Update the import at ~line 23: change `normalize_effort` to `normalize_complexity`.\n2. At ~line 326: change `normalize_effort(item.get('effort'))` → `normalize_complexity(item.get('complexity', ''))`\n3. At ~line 336: change `'effort': effort` → `'complexity': effort` (and rename the variable to `complexity` for clarity)\n4. At ~line 445: change `normalize_effort(candidate.get('effort', ''))` → `normalize_complexity(candidate.get('complexity', ''))` and rename variable `ceff` → `ccpx`\n5. At ~line 447: change `metadata['effort'] = ceff` → `metadata['complexity'] = ccpx`\n6. At ~line 528: change `normalize_effort(candidate.get('effort', ''))` → `normalize_complexity(candidate.get('complexity', ''))`\n7. At ~line 530: change `metadata['effort'] = effort` → `metadata['complexity'] = complexity`\n\nAlso check ~line 130 where `'effort': ''` appears in a skeleton dict — change to `'complexity': ''` if it's building task metadata; if it's the AI-parsed output template, update accordingly.\n\nThe AI executor returns JSON with `effort` field (schema defined in scaffold.py prompt); after scaffold.py is updated, the AI will return `complexity`. Until then, split.py parses whichever key is present. If the intermediate compat is needed, also check `candidate.get('effort', '')` as fallback."
human: false
model: "sonnet"
executor: "onward-exec"
depends_on:
- "TASK-053"
files:
- "src/onward/split.py"
acceptance:
- "normalize_complexity is imported; normalize_effort import is removed"
- "All metadata writes use 'complexity' key not 'effort'"
- "Zero grep matches for normalize_effort in split.py"
- "Zero grep matches for metadata\\[.effort. in split.py"
created_at: "2026-03-21T20:23:52Z"
updated_at: "2026-03-21T20:57:21Z"
effort: "s"
run_count: 1
last_run_status: "completed"
---

# Context

In `src/onward/split.py`:

1. Update the import at ~line 23: change `normalize_effort` to `normalize_complexity`.
2. At ~line 326: change `normalize_effort(item.get('effort'))` → `normalize_complexity(item.get('complexity', ''))`
3. At ~line 336: change `'effort': effort` → `'complexity': effort` (and rename the variable to `complexity` for clarity)
4. At ~line 445: change `normalize_effort(candidate.get('effort', ''))` → `normalize_complexity(candidate.get('complexity', ''))` and rename variable `ceff` → `ccpx`
5. At ~line 447: change `metadata['effort'] = ceff` → `metadata['complexity'] = ccpx`
6. At ~line 528: change `normalize_effort(candidate.get('effort', ''))` → `normalize_complexity(candidate.get('complexity', ''))`
7. At ~line 530: change `metadata['effort'] = effort` → `metadata['complexity'] = complexity`

Also check ~line 130 where `'effort': ''` appears in a skeleton dict — change to `'complexity': ''` if it's building task metadata; if it's the AI-parsed output template, update accordingly.

The AI executor returns JSON with `effort` field (schema defined in scaffold.py prompt); after scaffold.py is updated, the AI will return `complexity`. Until then, split.py parses whichever key is present. If the intermediate compat is needed, also check `candidate.get('effort', '')` as fallback.

# Scope

- In `src/onward/split.py`:

1. Update the import at ~line 23: change `normalize_effort` to `normalize_complexity`.
2. At ~line 326: change `normalize_effort(item.get('effort'))` → `normalize_complexity(item.get('complexity', ''))`
3. At ~line 336: change `'effort': effort` → `'complexity': effort` (and rename the variable to `complexity` for clarity)
4. At ~line 445: change `normalize_effort(candidate.get('effort', ''))` → `normalize_complexity(candidate.get('complexity', ''))` and rename variable `ceff` → `ccpx`
5. At ~line 447: change `metadata['effort'] = ceff` → `metadata['complexity'] = ccpx`
6. At ~line 528: change `normalize_effort(candidate.get('effort', ''))` → `normalize_complexity(candidate.get('complexity', ''))`
7. At ~line 530: change `metadata['effort'] = effort` → `metadata['complexity'] = complexity`

Also check ~line 130 where `'effort': ''` appears in a skeleton dict — change to `'complexity': ''` if it's building task metadata; if it's the AI-parsed output template, update accordingly.

The AI executor returns JSON with `effort` field (schema defined in scaffold.py prompt); after scaffold.py is updated, the AI will return `complexity`. Until then, split.py parses whichever key is present. If the intermediate compat is needed, also check `candidate.get('effort', '')` as fallback.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/split.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- normalize_complexity is imported; normalize_effort import is removed
- All metadata writes use 'complexity' key not 'effort'
- Zero grep matches for normalize_effort in split.py
- Zero grep matches for metadata\[.effort. in split.py

# Handoff notes
