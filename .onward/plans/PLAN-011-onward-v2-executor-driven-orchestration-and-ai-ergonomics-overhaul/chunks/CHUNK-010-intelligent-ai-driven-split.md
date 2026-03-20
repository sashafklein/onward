---
id: "CHUNK-010"
type: "chunk"
plan: "PLAN-011"
project: ""
title: "Intelligent AI-driven split"
status: "open"
description: "Wire onward split to the executor for real AI decomposition. Port nb repo chunking and task-sizing patterns."
priority: "high"
model: "sonnet-latest"
estimated_files: 15
depends_on:
  - "CHUNK-008"
created_at: "2026-03-20T15:52:26Z"
updated_at: "2026-03-20T15:52:26Z"
---

# Summary

Make `onward split` actually intelligent. Wire it to the executor so AI models decompose plans into chunks and chunks into tasks. Port the battle-tested patterns from nb's delivery pipeline: 20-30 file chunks with file touch maps, <=6 file self-contained tasks with model labels.

# Scope

- Wire `onward split PLAN-X` to send plan body + prompt to executor
- Wire `onward split CHUNK-X` to send chunk body + prompt to executor
- Rewrite `.onward/prompts/split-plan.md` with nb chunk.md patterns
- Rewrite `.onward/prompts/split-chunk.md` with nb plan-to-beads.md patterns
- Validate split output (sizing, dependency DAG, required fields)
- Keep `--heuristic` flag for offline/no-executor fallback
- Dry-run shows validation warnings alongside preview

# Out of scope

- Parallel chunk execution
- Auto-split on plan creation (split is always explicit)

# Dependencies

- CHUNK-008 (executor must be wired up to call AI)

# Expected files/systems involved

- `src/onward/split.py` — executor-backed split, validation
- `.onward/prompts/split-plan.md` — rewritten prompt
- `.onward/prompts/split-chunk.md` — rewritten prompt
- `src/onward/cli_commands.py` — --heuristic flag
- `tests/test_cli_split.py` — updated for executor-backed split

# Completion criteria

- [ ] `onward split PLAN-X` sends plan to AI and creates well-sized chunks
- [ ] `onward split CHUNK-X` sends chunk to AI and creates self-contained tasks
- [ ] Split prompts include file sizing rules, self-containment requirements, model labels
- [ ] Validation catches oversized chunks (>35 files) and tasks (>9 files)
- [ ] `--heuristic` flag preserves old behavior for offline use
- [ ] Dry-run shows validation warnings
