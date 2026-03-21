---
id: "TASK-061"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-016"
project: ""
title: "Docs: update effort→complexity references in documentation"
status: "open"
description: "Update the following documentation files to replace `effort` sizing terminology with `complexity`:\n\n**docs/CAPABILITIES.md:**\n- Replace any mention of `effort: xs|s|m|l|xl` with `complexity: low|medium|high`\n- Update any `--effort` CLI flag references to `--complexity`\n- Update descriptions of effort tiers (xs/s/m/l/xl) to complexity levels (low/medium/high)\n\n**docs/WORK_HANDOFF.md:**\n- Same substitutions: `--effort` → `--complexity`, `xs|s|m|l|xl` → `low|medium|high`\n- Update any examples showing `effort:` frontmatter to `complexity:`\n\n**docs/FUTURE_ROADMAP.md:**\n- Same substitutions if present\n\n**docs/AI_OPERATOR.md:**\n- Same substitutions if present\n- Note the compat fallback: tasks with old `effort:` frontmatter will still resolve the executor model correctly (config.py reads complexity first then falls back to effort)\n\nRead each file before editing — some may have few or no effort references. Only edit files that actually contain the old terminology."
human: false
model: "haiku"
executor: "onward-exec"
depends_on: []
files:
- "docs/CAPABILITIES.md"
- "docs/WORK_HANDOFF.md"
- "docs/FUTURE_ROADMAP.md"
- "docs/AI_OPERATOR.md"
acceptance:
- "Zero grep matches for '--effort' in docs/ directory"
- "Zero grep matches for 'effort: xs' or 'xs|s|m|l|xl' in docs/ directory"
- "Docs correctly describe --complexity flag with low|medium|high values"
- "AI_OPERATOR.md (or equivalent) documents the effort→complexity compat fallback if it previously described effort-based model resolution"
created_at: "2026-03-21T20:23:52Z"
updated_at: "2026-03-21T20:23:52Z"
effort: "s"
---

# Context

Update the following documentation files to replace `effort` sizing terminology with `complexity`:

**docs/CAPABILITIES.md:**
- Replace any mention of `effort: xs|s|m|l|xl` with `complexity: low|medium|high`
- Update any `--effort` CLI flag references to `--complexity`
- Update descriptions of effort tiers (xs/s/m/l/xl) to complexity levels (low/medium/high)

**docs/WORK_HANDOFF.md:**
- Same substitutions: `--effort` → `--complexity`, `xs|s|m|l|xl` → `low|medium|high`
- Update any examples showing `effort:` frontmatter to `complexity:`

**docs/FUTURE_ROADMAP.md:**
- Same substitutions if present

**docs/AI_OPERATOR.md:**
- Same substitutions if present
- Note the compat fallback: tasks with old `effort:` frontmatter will still resolve the executor model correctly (config.py reads complexity first then falls back to effort)

Read each file before editing — some may have few or no effort references. Only edit files that actually contain the old terminology.

# Scope

- Update the following documentation files to replace `effort` sizing terminology with `complexity`:

**docs/CAPABILITIES.md:**
- Replace any mention of `effort: xs|s|m|l|xl` with `complexity: low|medium|high`
- Update any `--effort` CLI flag references to `--complexity`
- Update descriptions of effort tiers (xs/s/m/l/xl) to complexity levels (low/medium/high)

**docs/WORK_HANDOFF.md:**
- Same substitutions: `--effort` → `--complexity`, `xs|s|m|l|xl` → `low|medium|high`
- Update any examples showing `effort:` frontmatter to `complexity:`

**docs/FUTURE_ROADMAP.md:**
- Same substitutions if present

**docs/AI_OPERATOR.md:**
- Same substitutions if present
- Note the compat fallback: tasks with old `effort:` frontmatter will still resolve the executor model correctly (config.py reads complexity first then falls back to effort)

Read each file before editing — some may have few or no effort references. Only edit files that actually contain the old terminology.

# Out of scope

- None specified.

# Files to inspect

- `docs/CAPABILITIES.md`
- `docs/WORK_HANDOFF.md`
- `docs/FUTURE_ROADMAP.md`
- `docs/AI_OPERATOR.md`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- Zero grep matches for '--effort' in docs/ directory
- Zero grep matches for 'effort: xs' or 'xs|s|m|l|xl' in docs/ directory
- Docs correctly describe --complexity flag with low|medium|high values
- AI_OPERATOR.md (or equivalent) documents the effort→complexity compat fallback if it previously described effort-based model resolution

# Handoff notes
