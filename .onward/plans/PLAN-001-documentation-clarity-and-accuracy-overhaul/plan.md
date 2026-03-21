---
id: "PLAN-001"
type: "plan"
project: "onward"
title: "Documentation clarity and accuracy overhaul"
status: "completed"
description: ""
priority: "medium"
model: "claude-opus-4-5"
created_at: "2026-03-21T04:12:01Z"
updated_at: "2026-03-21T04:16:04Z"
---

# Summary

Fix factual errors, stale references, and fragmented explanations across all Onward documentation so that a new user can install, configure, and start using Onward (especially the executor and work enqueueing) without confusion.

# Problem

After a thorough audit of all docs against the source code:
- AI_OPERATOR.md anti-pattern #3 is factually wrong about `onward split` default behavior
- INSTALLATION.md config reference uses deprecated legacy model keys (`task_default`, `split_default`, `review_default`) instead of the current tiered keys
- Multiple docs reference a `start` command that no longer exists
- The executor story is spread across 5+ files with no clear entry point for "how does `onward work` actually work?"
- CONTRIBUTION.md title ("Noob Guide") doesn't match its actual role as the developer/contributor guide
- README config example in "Artifact Anatomy" shows `blocked_by` without mentioning the preferred `depends_on`

# Goals

- Fix every factual error found during audit
- Update the INSTALLATION.md config reference to match the current scaffold defaults
- Remove all stale `start` command references
- Add a clear executor overview section to WORK_HANDOFF.md or README
- Make the "install → configure → first run" path obvious and linear

# Non-goals

- Rewriting the entire doc suite from scratch
- Adding new features
- Changing CLI behavior

# Proposed approach

Single chunk, multiple tasks:
1. Fix AI_OPERATOR.md anti-pattern #3 (factual error about split)
2. Update INSTALLATION.md config reference to use tiered model keys
3. Remove stale `start` command references from README, LIFECYCLE, CONTRIBUTION
4. Update README artifact anatomy to prefer `depends_on` over `blocked_by`
5. Add a concise "How `onward work` works" section to README or WORK_HANDOFF.md
6. Rename CONTRIBUTION.md title to reflect its actual purpose

# Acceptance criteria

- No documentation references to `onward start` command
- AI_OPERATOR.md correctly describes `onward split` as executor-backed by default
- INSTALLATION.md config example matches scaffold.py DEFAULT_FILES
- `pytest tests/test_docs_consistency.py` passes
- All cross-doc links are valid
