# Onward v1 Product Spec

> Implementation note (March 19, 2026): active scaffold uses `.onward.config.yaml` and `.onward/plans/`.

## 1. Summary

**Onward** is a git-native planning and execution tool for AI-assisted software development.

It is built around a simple idea:

- plans, chunks, and tasks should live in the repo as markdown
- state should be human-readable and editable
- the CLI should help organize, inspect, and advance work
- model orchestration should stay minimal until explicit execution time
- `onward work` is the boundary where Onward hands execution to Ralph

Onward is **not** meant to be a generic project management platform. It is an opinionated personal workflow tool optimized for one developer running AI-heavy implementation loops inside code repositories.

The core value is **maintaining forward momentum** while keeping planning artifacts transparent, structured, and easy to sync across environments.

---

## 2. Product framing

Onward is best thought of as:

> a repo-native momentum engine for AI-assisted coding

Not:

- a generic PM tool
- a ticketing system for large teams
- a web app
- a database-backed planner
- a full agent framework

Onward should be strongest at:

- creating and organizing plan/chunk/task artifacts
- showing what exists, what is active, and what just finished
- keeping task metadata visible in markdown frontmatter
- handing bounded task execution off to Ralph
- recording execution progress and outcomes
- capturing newly discovered follow-up work while execution is happening

---

## 3. Core principles

### 3.1 Markdown-native
All core planning artifacts are markdown files with frontmatter.

### 3.2 Git-native
The source of truth lives in the filesystem and can be committed, diffed, branched, synced, and reviewed.

### 3.3 Opinionated
Onward uses a fixed hierarchy:

- plan
- chunk
- task

These terms and meanings are built in. v1 does **not** attempt to support custom artifact taxonomies.

### 3.4 Lightweight until execution
Onward should focus on organization, status, and visibility first. It should not eagerly orchestrate models during basic artifact creation.

### 3.5 Explicit execution boundary
`onward work` is where Onward begins orchestrating actual AI execution via Ralph.

### 3.6 Local-first, sync-capable
Onward should work entirely locally, but also support syncing planning artifacts to either:

- a branch in the current repo
- a separate repo dedicated to shared plan state

### 3.7 Archive by removal from git
Archived plans move into `.onward/plans/.archive/`, which is gitignored so they naturally disappear from versioned state.

---

## 4. Scope of v1

Onward v1 includes:

- repo-local plan storage
- markdown templates for plan/chunk/task/hook/run
- frontmatter-based metadata
- commands for creating, listing, showing, starting, completing, canceling, splitting, and working
- derived views like `progress`, `recent`, and `next`
- local mode and shared sync mode
- optional separate sync repo support
- plan archiving into `.onward/plans/.archive/`
- Ralph integration at `onward work`
- shell hooks and markdown agent hooks

Onward v1 does **not** include:

- a web UI
- a database
- arbitrary workflow taxonomies
- multi-user locking
- elaborate scheduler logic
- generic executor abstraction beyond what is needed to call Ralph cleanly
- background daemon infrastructure

---

## 5. Information model

Onward has five core artifact types:

## 5.1 Plan
A high-level initiative.

A plan should define:

- what is being built or changed
- why it matters
- scope and non-goals
- architecture or approach
- sequencing thoughts
- decomposition into chunks

## 5.2 Chunk
A bounded implementation unit within a plan.

A chunk should generally map to:

- one coherent deliverable
- one manageable PR series
- one execution stream that may contain multiple tasks

Chunks exist primarily to keep plans executable and to bound implementation size.

## 5.3 Task
The smallest self-contained execution unit.

A task should be:

- understandable on its own
- scoped tightly
- executable by one human or one AI worker loop
- accompanied by acceptance criteria
- associated with a preferred model and execution instructions
- explicit about whether human action is required

Tasks are generally created close to build time.

## 5.4 Hook
A reusable execution-time instruction or command triggered before or after work.

Hooks can be:

- shell hooks
- markdown agent hooks

Markdown hooks are especially important for review, follow-up planning, cleanup, and synthesis.

## 5.5 Run
A record of an execution attempt.

Runs capture:

- what was worked on
- when it started and ended
- what model/executor was used
- status/outcome
- notes or summary

---

## 6. State model

Use a uniform minimal state model across plans, chunks, and tasks:

- `open`
- `in_progress`
- `completed`
- `canceled`

No dedicated `blocked` state in v1.

Blocking should instead be represented with optional metadata fields such as:

```yaml
blocked_by:
  - TASK-003
block_reason: Waiting on API decision
```

This keeps status simple while preserving useful dependency information.

Tasks may also carry a `human: true|false` boolean so human-only blocking work can be surfaced directly.

---

## 7. Repo layout

Onward uses one config file and one directory at repo root:

```txt
.onward.config.yaml
.onward/
```

## 7.1 `.onward/`
Tooling configuration and templates.

Suggested layout:

```txt
.onward/
  plans/
    index.yaml
    recent.yaml
    PLAN-001-unified-onboarding-rewrite/
      plan.md
      research.md
      chunks/
        CHUNK-001-backend-foundation.md
        CHUNK-002-frontend-flow.md
      tasks/
        TASK-001-schema.md
        TASK-002-endpoints.md
      runs/
        RUN-2026-03-18T12-00-00Z-TASK-001.md
  plans/.archive/
  templates/
    plan.md
    chunk.md
    task.md
    run.md
  hooks/
    post-task.md
    post-chunk.md
    review-task.md
  sync/
    .gitkeep
```
`.onward/plans/.archive/` must be gitignored.

---

## 8. Archiving behavior

When a plan is archived:

- its full plan directory is moved into `.onward/plans/.archive/`
- archived artifacts disappear from active git-tracked planning state
- active indexes exclude archived items

This is intentionally destructive from the perspective of the active planning workspace, but history still exists locally unless manually deleted.

### 8.1 Git behavior
Add at least:

```txt
.onward/plans/.archive/
```

to `.gitignore`.

### 8.2 Command
```bash
onward archive PLAN-001
```

This should:

- validate the plan exists
- move the plan folder into `.onward/plans/.archive/`
- regenerate indexes
- remove it from active views

---

## 9. Frontmatter schema

Onward should keep schema simple and explicit.

## 9.1 Common fields
Shared across plan/chunk/task:

```yaml
---
id: PLAN-001
type: plan
title: Unified onboarding rewrite
status: open
created_at: 2026-03-18T12:00:00Z
updated_at: 2026-03-18T12:00:00Z
tags: [onboarding, architecture]
project: onboarding
---
```

## 9.2 Plan fields

```yaml
---
id: PLAN-001
type: plan
title: Unified onboarding rewrite
status: open
description: Consolidate onboarding flows into one unified architecture
priority: high
model: gpt-5
created_at: 2026-03-18T12:00:00Z
updated_at: 2026-03-18T12:00:00Z
---
```

## 9.3 Chunk fields

```yaml
---
id: CHUNK-001
type: chunk
plan: PLAN-001
title: Backend foundation
status: open
description: Add schema and APIs needed for unified onboarding
priority: high
model: gpt-5
created_at: 2026-03-18T12:00:00Z
updated_at: 2026-03-18T12:00:00Z
---
```

## 9.4 Task fields

```yaml
---
id: TASK-001
type: task
plan: PLAN-001
chunk: CHUNK-001
project: onboarding
title: Add onboarding_session table
status: open
description: Add DB schema and migration for onboarding sessions
human: false
model: gpt-5-mini
executor: ralph
depends_on: []
blocked_by: []
block_reason: null
files:
  - packages/db/schema.ts
  - packages/db/migrations/
acceptance:
  - onboarding_session table exists
  - migration applies cleanly
  - type generation succeeds
  - relevant tests pass
created_at: 2026-03-18T12:00:00Z
updated_at: 2026-03-18T12:00:00Z
---
```

### Notes on task metadata

- `blocked_by` is a first-class frontmatter field and should always be present (empty list when unblocked).
- `human: true` marks tasks that require a person rather than an agent worker.
- `project` is optional metadata for cross-plan grouping and filtering.

## 9.5 Hook fields

```yaml
---
id: HOOK-post-task
type: hook
trigger: task.completed
model: gpt-5
executor: ralph
scope: repo
created_at: 2026-03-18T12:00:00Z
updated_at: 2026-03-18T12:00:00Z
---
```

## 9.6 Run fields

```yaml
---
id: RUN-2026-03-18T12-00-00Z-TASK-001
type: run
target: TASK-001
plan: PLAN-001
chunk: CHUNK-001
status: in_progress
executor: ralph
model: gpt-5-mini
started_at: 2026-03-18T12:00:00Z
ended_at: null
---
```

---

## 10. Markdown body templates

## 10.1 Plan body

```md
# Summary

# Problem

# Goals

# Non-goals

# Context

# Proposed approach

# Risks

# Chunking strategy

# Notes
```

## 10.2 Chunk body

```md
# Summary

# Scope

# Out of scope

# Dependencies

# Expected files/systems involved

# Completion criteria

# Notes
```

## 10.3 Task body

```md
# Context

# Scope

# Out of scope

# Files to inspect

# Implementation notes

# Acceptance criteria

# Handoff notes
```

## 10.4 Hook body

Markdown hook bodies are direct instructions to the executing agent.

Example sections:

```md
# Purpose

# Inputs

# Instructions

# Required output
```

---

## 11. Config

Primary config lives at:

```txt
.onward.config.yaml
```

This file defines:

- paths
- sync mode
- Ralph integration defaults
- default models
- hooks
- worktree behavior

Example:

```yaml
version: 1

paths:
  plans_dir: .onward/plans

sync:
  mode: local
  branch: onward
  repo: null
  worktree_path: .onward/sync

ralph:
  command: ralph
  enabled: true
  default_executor: ralph

models:
  default: gpt-5
  task_default: gpt-5-mini
  split_default: gpt-5
  review_default: gpt-5

work:
  sequential_by_default: true
  create_worktree: true
  base_branch: main

hooks:
  pre_task_shell: []
  post_task_shell: []
  pre_task_markdown: null
  post_task_markdown: .onward/hooks/post-task.md
  post_chunk_markdown: .onward/hooks/post-chunk.md
```

---

## 12. Sync modes

Onward supports two modes.

## 12.1 Local mode
All planning artifacts stay in the current repo and current branch. No syncing required.

## 12.2 Shared sync mode
Planning artifacts are synchronized to a shared location.

This shared location can be either:

- a branch in the same repo
- a separate repo dedicated to plan state

### 12.2.1 Same-repo branch mode
Example:

- code work on normal branches
- planning artifacts sync to branch `onward`

### 12.2.2 Separate sync repo mode
This is explicitly supported for workflows where an overseer agent, such as OpenClaw, manages task state outside the main project repo.

In this mode:

- source repo contains `.onward/plans/`
- Onward syncs `.onward/plans/` to another repo
- another agent can update shared task state there
- the project repo can later pull/sync those changes back

This allows one big shared task list across environments.

### 12.2.3 Sync expectations
Sync is best-effort and file-based. v1 does not attempt sophisticated merge conflict resolution.

Onward should expose commands such as:

```bash
onward sync push
onward sync pull
onward sync status
```

---

## 13. CLI philosophy

Onward should be strongest at:

- creating artifacts
- showing current state
- splitting larger artifacts into smaller ones
- handing execution to Ralph when explicitly asked

Onward should **not** automatically kick off models for simple creation commands unless explicitly requested.

This means the clean boundary is:

```bash
onward new plan "Unified onboarding rewrite" --description "..."
```

creates a plan artifact only.

Then separate commands can be used to populate or decompose it.

This keeps creation deterministic and keeps orchestration from leaking into basic organization commands.

---

## 14. CLI commands

## 14.1 Initialization

```bash
onward init
onward doctor
onward sync status
```

### `onward init`
Creates:

- `.onward/`
- `.onward/plans/`
- templates
- default hooks
- `.gitignore` update for `.onward/plans/.archive/`

### `onward doctor`
Validates:

- required directories exist
- config is parseable
- frontmatter is valid
- references are valid
- indexes can be regenerated

---

## 14.2 Creation

```bash
onward new plan "Unified onboarding rewrite" --description "Consolidate onboarding flows"
onward new chunk PLAN-001 "Backend foundation" --description "Schema + API work"
onward new task CHUNK-001 "Add onboarding_session table" --description "DB schema and migration"
```

These commands:

- create files from templates
- assign IDs
- populate frontmatter
- do not invoke models by default

---

## 14.3 Viewing and navigation

```bash
onward list
onward list --project onboarding
onward list --blocking
onward list --blocking --human
onward show PLAN-001
onward show CHUNK-001
onward show TASK-001
onward tree PLAN-001
onward progress
onward recent
onward next
```

### `onward progress`
Shows everything currently in progress, including:

- plans in progress
- chunks in progress
- tasks in progress
- active runs
- assigned models/executors if available

### `onward recent`
Shows recently completed items in reverse chronological order.

### `onward next`
Shows best next open work, likely prioritizing:

- open tasks with no unmet dependencies
- tasks within chunks already in progress
- otherwise next open chunks/plans lacking tasks

### `onward list --blocking --human`
Shows open tasks where:

- `human: true`
- at least one other open artifact is blocked by them (via `blocked_by` or unmet dependencies)

This supports fast triage of the smallest human actions needed to unblock agent execution.

---

## 14.4 State changes

```bash
onward start TASK-001
onward complete TASK-001
onward cancel TASK-001
onward start CHUNK-001
onward complete CHUNK-001
onward archive PLAN-001
```

These commands should:

- update frontmatter status
- update timestamps
- regenerate indexes
- create run records when appropriate

---

## 14.5 Splitting / decomposition

```bash
onward split PLAN-001
onward split CHUNK-001
```

Onward should determine artifact type from ID or file lookup.

### `onward split PLAN-001`
Default meaning:

- read the plan doc
- generate one or more chunk docs
- use configured default split model
- write proposed chunk artifacts to disk

### `onward split CHUNK-001`
Default meaning:

- read the chunk doc
- generate one or more task docs
- use configured default split model
- create task files with acceptance criteria and model defaults

This is where some automation is desirable.

Unlike `new`, `split` is allowed to invoke a model by default because decomposition is inherently generative.

---

## 14.6 Execution

```bash
onward work TASK-001
onward work CHUNK-001
```

This is the main execution boundary.

### `onward work TASK-001`
Onward should:

- resolve the task file
- inspect frontmatter
- choose the specified model or configured default
- create a run record
- execute any pre-task shell hooks
- optionally execute a pre-task markdown hook via Ralph
- enqueue the task to Ralph
- monitor or poll status as needed
- on completion, execute post-task hooks
- update task status and run record
- surface result to the user

### `onward work CHUNK-001`
Onward should:

- gather tasks in the chunk
- order them, respecting dependencies where possible
- process open tasks sequentially by default
- optionally create or use a worktree
- invoke Ralph task by task
- run hooks between tasks
- stop on failure or blocking condition unless configured otherwise
- update chunk status as it progresses
- mark chunk completed when all tasks complete
- optionally trigger post-chunk hook

This command is allowed to perform queue management and execution coordination because it is explicitly the orchestration boundary.

### 14.6.1 Feedback loop: adding discovered follow-up work

During `onward work`, workers should be guided to capture newly discovered work explicitly:

- blocker tasks
- refactor tasks
- cleanup tasks
- deferred enhancement tasks

Recommended behavior:

- create these as new tasks under the current chunk by default
- allow a worker to attach them to another chunk/plan when more appropriate
- include concise rationale in task body
- mark as `human: true` when human intervention is required

This can be implemented through default worker guidance and/or a post-task markdown hook.

---

## 14.7 Reporting

```bash
onward report
onward report --project onboarding
```

`onward report` should produce a consolidated, colorized terminal report with readable ASCII tables that includes:

- in-progress plans/chunks/tasks
- next suggested work
- open blockers
- open human-blocking tasks
- recently completed work
- grouped view of open plans with nested chunks/tasks

`--project` narrows report output to artifacts tagged with the selected project.

---

## 15. Ralph integration

v1 should couple to Ralph directly rather than abstracting over many executors.

That is the simplest and most useful boundary.

## 15.1 Integration stance
Onward does not need a generic executor plugin system in v1.

It only needs enough structure to:

- build an execution payload from a task
- call `ralph`
- track the resulting run
- apply hooks and status transitions

## 15.2 Ralph command integration
Config should allow specifying:

- command name/path
- default args
- model mapping behavior

Example:

```yaml
ralph:
  command: ralph
  args: []
```

## 15.3 Task handoff packet
Onward should construct a clear payload for Ralph from:

- task frontmatter
- task body
- linked plan/chunk context as needed
- hook-generated instructions if applicable
- model and executor metadata

Onward may initially hand Ralph a synthesized prompt or temp file.

## 15.4 Status tracking
Onward should track:

- queued
- running
- completed
- failed

at the **run level**, even if artifact-level status remains the simpler four-state model.

This keeps execution detail out of the main artifact state model.

---

## 16. Hook model

Onward supports two hook types.

## 16.1 Shell hooks
Configured in YAML and executed directly.

Useful for:

- tests
- lint
- formatting
- worktree setup
- git commands

## 16.2 Markdown hooks
Markdown documents with frontmatter specifying trigger and model.

Useful for:

- review summaries
- proposing follow-up tasks
- synthesizing implementation notes
- cleanup instructions
- chunk retrospectives

### 16.2.1 Example triggers

- `task.pre`
- `task.completed`
- `chunk.completed`

### 16.2.2 Example locations

Repo-level:

```txt
.onward/hooks/post-task.md
```

Plan-level override:

```txt
.onward/plans/PLAN-001-foo/hooks/post-task.md
```

### 16.2.3 Hook precedence
For v1:

1. plan-level hook if present
2. repo-level hook if present
3. no hook

---

## 17. Worktrees

Onward should support worktree-based execution during `onward work`, especially for chunk execution.

Expected flow:

- create or reuse a worktree
- run tasks sequentially in that worktree
- keep changes isolated from main working tree

This should be configurable and enabled by default if feasible.

Example config:

```yaml
work:
  create_worktree: true
  worktree_root: .worktrees
  base_branch: main
```

---

## 18. Derived indexes

Onward may maintain derived files such as:

- `.onward/plans/index.yaml`
- `.onward/plans/recent.yaml`

These are not the canonical source of truth.

The canonical source is the artifact files themselves.

Indexes exist to make listing and display fast and simple.

### `index.yaml`
May contain summaries of active plans/chunks/tasks.

### `recent.yaml`
May contain recently completed artifacts and runs.

These should be regenerable from disk.

---

## 19. UX examples

## 19.1 Create a plan manually

```bash
onward new plan "Unified onboarding rewrite" --description "Consolidate onboarding flows into one architecture"
```

Then edit the generated `plan.md`.

## 19.2 Split into chunks

```bash
onward split PLAN-001
```

Onward uses the configured split model to propose chunk files.

## 19.3 Split a chunk into tasks

```bash
onward split CHUNK-001
```

Onward generates task files with frontmatter, acceptance criteria, and model defaults.

## 19.4 Execute a task

```bash
onward work TASK-001
```

Onward calls Ralph, tracks the run, and updates progress.

## 19.5 Execute a whole chunk

```bash
onward work CHUNK-001
```

Onward works through chunk tasks sequentially in a worktree, reporting status through `progress` and `recent`.

---

## 20. Non-goals

Onward v1 should not attempt to solve all of the following:

- arbitrary collaboration semantics
- perfect merge conflict handling
- full DAG scheduling
- distributed job queueing
- multiple executor frameworks
- branch-aware code-state reconciliation between plan state and source state
- complex permissions
- web dashboards

---

## 21. MVP implementation priorities

## Priority 1: file structure and schema

- init
- templates
- frontmatter parsing
- ID generation
- creation commands

## Priority 2: visibility

- list
- show
- tree
- progress
- recent
- next
- report
- blocking filters (`--blocking`, `--human`, `--project`)

## Priority 3: state transitions

- start
- complete
- cancel
- archive
- sync indexes

## Priority 4: split

- split plan -> chunks
- split chunk -> tasks

## Priority 5: work / Ralph integration

- work task
- work chunk sequentially
- run records
- hook handling
- worktree support

## Priority 6: sync

- local mode
- same-repo branch sync
- separate repo sync

---

## 22. Open implementation questions for Codex

These do not block v1, but Codex should make pragmatic choices.

### 22.1 ID format
Suggested:

- `PLAN-001`
- `CHUNK-001`
- `TASK-001`
- `RUN-<timestamp>-TASK-001`

Need decision on whether chunk/task IDs are global or scoped per plan.

Recommended v1 answer: **global IDs**, simpler lookup.

### 22.2 File naming
Recommended:

- IDs plus slugged title

Example:

- `PLAN-001-unified-onboarding-rewrite`
- `CHUNK-001-backend-foundation.md`
- `TASK-001-add-onboarding-session-table.md`

### 22.3 How much linked context to send to Ralph
Recommended:

- task body always
- task frontmatter always
- chunk summary if present
- plan summary if present
- not entire repository plan tree by default

### 22.4 How to monitor Ralph runs
Recommended:

- start with synchronous invocation or simple polling
- do not build a sophisticated event bus in v1

### 22.5 Where should discovered follow-up tasks go by default?

Recommended v1 answer:

- same chunk by default
- allow explicit reassignment to another chunk/plan
- always include `blocked_by`, `human`, and `project` metadata when known

---

## 23. Final design stance

Onward should feel like this:

- easy to inspect
- easy to edit
- pleasant to use from CLI
- strongly oriented toward forward motion
- opinionated enough to stay simple
- tightly integrated with Ralph at execution time

The center of gravity should remain:

- plans/chunks/tasks as markdown
- `split` for decomposition
- `progress` and `recent` for visibility
- `work` for execution

That is the heart of the tool.

---

## 24. Suggested first implementation milestone

The first milestone should be:

- `onward init`
- `onward new plan|chunk|task`
- `onward list`
- `onward show`
- `onward progress`
- `onward recent`
- `onward start|complete|cancel`
- `onward archive`
- `onward split PLAN`
- `onward split CHUNK`
- `onward work TASK`

Then second milestone:

- `onward work CHUNK`
- worktree support
- markdown hooks
- sync push/pull/status

That would already be a very strong v1.
