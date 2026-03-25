---
id: "PLAN-008"
type: "plan"
project: ""
title: "Explicit artifact ranking for backlog ordering"
status: "completed"
description: "Pull Linear sortOrder into Onward frontmatter and use it (with priority) to drive roadmap, next, and report ordering"
priority: "high"
model: "opus"
created_at: "2026-03-25T02:39:16Z"
updated_at: "2026-03-25T04:02:05Z"
---

# Summary

When Onward syncs with Linear (`onward linear pull`), we already pull `priority` (mapped
to high/medium/low). But Linear also exposes `sortOrder` — a float representing the
user's manual drag-and-drop ordering. We currently fetch it but discard it. This plan
stores `sortOrder` as `linear_sort_order` in plan frontmatter and uses both `priority`
and `linear_sort_order` to drive `onward roadmap`, `onward next`, and report ordering.

# Problem

`onward next` ignores priority entirely — it picks the next task based on in-progress
status and ID string ordering. `onward roadmap` sorts by priority tier but breaks ties
by plan ID, losing the fine-grained ordering that users set up in Linear.

# Goals

- Store Linear's `sortOrder` as `linear_sort_order` in plan frontmatter during pull
- `onward roadmap` sorts plans by (priority tier, linear_sort_order, plan ID)
- `onward next` factors in plan priority + sort_order when ranking ready tasks
- Index fast-path includes priority and sort_order for correct ordering without full scan

# Non-goals

- Changing the three-tier priority system (high/medium/low)
- Adding a manual `rank` field for non-Linear users (future work)
- Changing chunk or task ordering within a plan

# End state

- [ ] `onward linear pull` writes `linear_sort_order` to plan frontmatter
- [ ] `onward roadmap` orders plans by priority tier, then by Linear sort order
- [ ] `onward next` prefers tasks from higher-priority, higher-ranked plans
- [ ] The index fast-path preserves priority and sort_order for correct ordering
- [ ] Existing tests pass; new tests cover the ordering behavior

# Proposed approach

## 1. New frontmatter field: `linear_sort_order`

Add `linear_sort_order` to `KNOWN_FIELDS["plan"]` in `artifacts.py`. This is a float
stored as a string in YAML frontmatter. Lower values = higher rank (matches Linear).

## 2. Linear pull changes

In `_do_linear_pull` (`cli_commands.py`):
- When **creating** new plans from Linear: include `linear_sort_order: issue.sort_order`
- When **updating** existing plans: detect sort_order changes and update the field
- Include sort_order changes in the change log output

## 3. Roadmap ordering

In `cmd_roadmap` (`cli_commands.py`):
- Change plan sort key from `(priority_rank, plan_id)` to
  `(priority_rank, linear_sort_order or inf, plan_id)`
- Plans with lower sort_order appear first within the same priority tier
- Plans without a sort_order (non-Linear) sort after Linear-ordered ones, by ID

## 4. Next artifact selection

In `select_next_artifact` (`artifacts.py`):
- Add helper `_plan_rank(plan, priority_order)` returning `(priority_rank, sort_order, plan_id)`
- Ready task sort key becomes:
  `(in_progress_chunk, in_progress_plan, plan_priority_rank, plan_sort_order, task_id)`
- Open chunks/plans fallback also uses `_plan_rank` for ordering

## 5. Index updates

In `regenerate_indexes` and `_artifact_from_index_row` (`artifacts.py`):
- Include `priority` and `linear_sort_order` in plan index rows
- Reconstruct these fields when loading from index so fast-path ordering is correct

# Acceptance criteria

- `onward linear pull` stores `linear_sort_order` on created and updated plans
- `onward roadmap` reflects Linear ordering within priority tiers
- `onward next` returns tasks from higher-priority plans first
- `pytest tests/test_linear.py` passes with new tests for sort_order syncing
- Full `pytest` suite passes
