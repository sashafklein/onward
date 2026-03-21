---
id: "TASK-039"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-010"
project: ""
title: "Rewrite split prompts with nb patterns"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:04Z"
updated_at: "2026-03-20T18:17:36Z"
---

# Context

The current split prompts (`.onward/prompts/split-plan.md` and `split-chunk.md`) are minimal JSON schema instructions with no decomposition intelligence. This task rewrites them with patterns adapted from the nb repo's delivery pipeline: file touch maps, dependency DAGs, sizing constraints, and self-containment rules. This makes AI-driven splitting produce well-structured, right-sized artifacts.

# Scope

- Rewrite `.onward/prompts/split-plan.md` with adapted content from nb `chunk.md` patterns:
  - 20-30 file target per chunk
  - File touch maps (must/likely/deferred categories)
  - Dependency DAG between chunks (output `depends_on` field per chunk)
  - Acceptance criteria per chunk
  - Self-containment requirements (each chunk must be independently testable)
  - Priority assignment guidance
- Rewrite `.onward/prompts/split-chunk.md` with adapted content from nb `plan-to-beads.md` patterns:
  - <=6 file target per task
  - Self-containment rules (specific file paths, inline context, no "see plan" references)
  - Model label suggestions (haiku for trivial, sonnet for standard, opus for complex)
  - Sizing validation guidance (warning at 7-9 files, must split if >9)
  - `depends_on` field per task for intra-chunk ordering
  - Acceptance criteria that are binary-checkable
- Update the JSON schema in both prompts to include the new fields (`depends_on`, `files`, `acceptance`, `effort`)
- Update the scaffold defaults in `scaffold.py` `DEFAULT_FILES` to match the new prompt content
- Update `normalize_chunk_candidates` and `normalize_task_candidates` in `split.py` to handle new fields (`depends_on`, `files`, `effort`)

# Out of scope

- Changing the executor invocation mechanism (TASK-038)
- Output validation and sizing enforcement (TASK-040)
- Changing how chunks/tasks are written to disk (the `prepare_*_writes` functions)
- Modifying the existing JSON envelope shape (`{"chunks": [...]}` / `{"tasks": [...]}`)

# Files to inspect

- `.onward/prompts/split-plan.md` — current 19-line minimal prompt to rewrite
- `.onward/prompts/split-chunk.md` — current 20-line minimal prompt to rewrite
- `src/onward/split.py` — `normalize_chunk_candidates`, `normalize_task_candidates`, `prepare_chunk_writes`, `prepare_task_writes`
- `src/onward/scaffold.py` — `DEFAULT_FILES` entries for both prompts
- Reference patterns (read for inspiration, don't copy verbatim): `/Users/sasha/code/nb/.cursor/commands/chunk.md`, `/Users/sasha/code/nb/.cursor/commands/plan-to-beads.md`

# Implementation notes

- The prompts must output strict JSON (no markdown fences). This constraint stays.
- The chunk JSON schema should expand to: `{title, description, priority, model, depends_on: [], files: {must: [], likely: [], deferred: []}, acceptance: []}`.
- The task JSON schema should expand to: `{title, description, acceptance: [], model, human, depends_on: [], files: [], effort: "xs|s|m|l|xl"}`.
- `normalize_chunk_candidates` needs to handle new optional fields: `depends_on` (list of chunk titles/IDs, resolved later), `files` (dict with must/likely/deferred), `acceptance` (list).
- `normalize_task_candidates` needs to handle: `depends_on` (list), `files` (list of paths), `effort` (string).
- For `depends_on` in split output: since IDs aren't assigned yet during split, the AI should output dependency references by title or index. The normalization step maps these to actual IDs after assignment. Consider: have the AI output `depends_on_index: [0, 2]` (0-based indices into the output array) which gets resolved to IDs.
- Keep the prompt tone directive-focused: tell the AI what to do, not what not to do.
- Both prompts should include a concrete example of the expected JSON output with the full schema.

# Acceptance criteria

- `split-plan.md` includes file touch map instructions, dependency DAG, 20-30 file target guidance, acceptance criteria per chunk
- `split-chunk.md` includes <=6 file target, self-containment rules, model label guidance, sizing warnings
- Both prompts include updated JSON schema examples with all new fields
- `normalize_chunk_candidates` handles `depends_on`, `files`, `acceptance` fields
- `normalize_task_candidates` handles `depends_on`, `files`, `effort` fields
- Scaffold defaults in `scaffold.py` match the new prompt content
- Existing split tests still pass (env override path unchanged)

# Handoff notes

- The `depends_on` resolution from indices to IDs is the trickiest part. Consider adding a post-normalization step in `cmd_split` that maps indices after IDs are assigned by `next_ids`.
- TASK-040 adds validation on top of this — sizing checks, dependency cycle detection, etc.
- The `prepare_chunk_writes` and `prepare_task_writes` functions may need updates to include new metadata fields (`files`, `effort`, chunk-level `acceptance`). If the scope is too large, create a follow-up task.
