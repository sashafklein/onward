---
id: "PLAN-006"
type: "plan"
project: ""
title: "review-plan CLI command"
status: "completed"
description: ""
priority: "medium"
model: "opus-latest"
created_at: "2026-03-19T05:51:01Z"
updated_at: "2026-03-19T05:53:53Z"
---

# Summary

Add a `review-plan PLAN_ID` command that spawns one or two model-backed reviews of a plan, writes the results to gitignored review artifacts, and announces them to the user.

# Goals

- New `onward review-plan PLAN_ID` CLI command
- Configurable `review.double_review` (default true): when true, enqueue two independent reviews (review_default model + default model); when false, just one (review_default)
- Thorough, structured review prompt focused on gaps, security, missing requirements, deployment risks
- Review artifacts written to `.onward/reviews/` (gitignored)
- Announce the review doc paths and recommend the user incorporate findings into the plan

# Non-goals

- Code review (PR diff review) — separate future command
- Interactive review editing or approval workflow
- Automatic plan modification based on review findings

# Proposed approach

1. Add `review` config section with `double_review: true` to default config template
2. Add `.onward/reviews/` to `GITIGNORE_LINES`
3. Add `DEFAULT_DIRECTORIES` entry for `.onward/reviews`
4. Add a review-plan prompt to `DEFAULT_FILES` at `.onward/prompts/review-plan.md`
5. Implement `_execute_plan_review(root, plan, model, label)` helper that:
   - Builds ralph command from config
   - Constructs review payload (type="review", plan metadata+body, prompt)
   - Invokes ralph via subprocess, captures stdout
   - Writes review output to `.onward/reviews/{PLAN_ID}-{timestamp}-{label}.md`
   - Returns the output path
6. Implement `cmd_review_plan(args)` that:
   - Loads config, resolves models
   - If double_review: run review_default then default
   - If single: run review_default only
   - Announces paths and recommends user review
7. Register `review-plan` subparser in `build_parser()`
8. Add tests in `tests/test_cli_review.py`

# Acceptance criteria

- `onward review-plan PLAN-001` invokes ralph with correct model and payload
- With `double_review: true`, two review files are created in `.onward/reviews/`
- With `double_review: false`, one review file is created
- `.onward/reviews/` is in GITIGNORE_LINES
- Review files contain structured markdown with assessment and findings table
- Tests cover both single and double review modes, and missing plan error
