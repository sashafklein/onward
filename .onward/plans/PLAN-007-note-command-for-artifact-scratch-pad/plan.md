---
id: "PLAN-007"
type: "plan"
project: ""
title: "Note command for artifact scratch pad"
status: "completed"
description: ""
priority: "medium"
model: "opus-latest"
created_at: "2026-03-19T14:26:46Z"
updated_at: "2026-03-19T14:31:28Z"
---

# Summary

Add a `note` command that provides a per-artifact scratch pad. Notes are timestamped entries stored in `.onward/notes/{ID}.md`, surfaced on completion/cancel, and included in work payloads.

# Goals

- `onward note ID "message"` appends a timestamped note
- `onward note ID` (no message) displays all notes for that artifact
- Notes stored in `.onward/notes/{ID}.md`, one file per artifact, append-only
- Artifact frontmatter updated with `has_notes: true` when first note is added
- `complete` and `cancel` display related notes inline
- `work` payload includes notes so the executor has full context
- Tests and docs

# Proposed approach

1. Add `.onward/notes` to DEFAULT_DIRECTORIES
2. Add helpers: `_notes_path()`, `_read_notes()`, `_append_note()`
3. Implement `cmd_note()` — add (with message) or show (without)
4. Update `_cmd_set_status()` to print notes on complete/cancel
5. Update `_execute_task_run()` payload to include notes
6. Register `note` subparser in `build_parser()`
7. Tests in `tests/test_cli_note.py`
8. Document in README.md and INSTALLATION.md

# Acceptance criteria

- `onward note TASK-001 "todo: check edge case"` creates `.onward/notes/TASK-001.md`
- `onward note TASK-001` prints the notes
- Artifact frontmatter gains `has_notes: true` after first note
- `onward complete TASK-001` prints "Related notes:" with the notes
- Work payload includes `notes` field when notes exist
- All existing tests still pass
