# Installation & Agent Setup

This document gets you from zero to **structured, agent-driven development tracked entirely through Onward.** Two phases:

1. **Install the CLI** (2 minutes)
2. **Wire up your agent** (5 minutes, but this is the part that matters)

Skip phase 2 and you have a nice CLI. Complete it and you have **an AI development workflow with persistent memory, structured plans, and nothing lost between sessions.**

---

## Phase 1: Install the CLI

### Requirements

- Python 3.11+
- A git repository (Onward is git-native — your plans live in the repo)

### Install

From the Onward source repo:

```bash
python3.11 -m pip install -e /path/to/onward-repo
```

Verify:

```bash
onward --help
```

You should see the full command list: `init`, `doctor`, `new`, `list`, `report`, `next`, `start`, `complete`, `sync`, `work`, etc.

### Initialize a Workspace

In any project repo where you want Onward-tracked development:

```bash
cd /path/to/your-project
onward init
onward doctor
```

`init` creates the `.onward/` directory structure, templates, and config.
`doctor` validates everything is wired up correctly.

You're installed. Now the important part.

---

## Phase 2: Agent Configuration

**This is where the magic happens.** Onward is designed to be the **exclusive** planning and execution tracking system for AI agents working in your repo. For this to work, your agent needs explicit, emphatic instructions to use Onward for ALL planning — no ad-hoc todo lists, no plans-in-chat, no scattered notes.

Below are ready-to-use configuration blocks for every major agent configuration format. **Pick the one that matches your setup and paste it in.**

---

### Option A: AGENTS.md Block

If your agent reads an `AGENTS.md` file (Codex, Claude Code, Cursor agents, etc.), add this block. Paste it near the top — it should be among the first things the agent reads.

````markdown
## Onward — Mandatory Project Orchestration

**CRITICAL: ALL planning, task tracking, and execution management in this repository
MUST go through Onward.** Do not maintain plans in chat, in comments, in scratch files,
or in your own memory. Onward is the single source of truth.

### The Rule

Every piece of work — from initial planning through final completion — is tracked as an
Onward artifact. No exceptions. If it's not in `.onward/plans/`, it doesn't exist.

### The Loop

This is your operating rhythm. Follow it relentlessly:

```
onward report --project <key>   ← See the full picture
onward next --project <key>     ← Pick the next thing
onward start <ID>               ← Claim it
... do the work ...
onward complete <ID>            ← Finish it
```

### Starting New Work

When the user describes a new initiative, feature, or project:

1. `onward new plan "<title>" --project <key>` — create the plan artifact
2. Edit the generated plan.md — fill in Summary, Goals, Proposed Approach, Acceptance Criteria
3. `onward split PLAN-XXX` or manually create chunks with `onward new chunk`
4. `onward split CHUNK-XXX` or manually create tasks with `onward new task`
5. `onward report --project <key>` — confirm the work is structured

### During Execution

- Run `onward start <ID>` BEFORE beginning any task
- Run `onward complete <ID>` AFTER finishing any task
- If you discover follow-up work, blockers, or refactors: IMMEDIATELY create a new task
  with `onward new task <CHUNK-ID> "<title>"` and set `blocked_by`, `human`, and `project`
  metadata in the frontmatter as appropriate
- Run `onward report` at the end of every work session to leave a clear picture for the
  next session or the next agent

### Situational Awareness

- `onward report --project <key>` — dashboard of everything: in-progress, next up,
  blockers, recent completions
- `onward list --blocking --human` — what human actions are blocking agent work
- `onward tree --project <key>` — hierarchical view of all plans/chunks/tasks
- `onward next --project <key>` — the single best thing to work on next
- `onward show <ID>` — full detail on any artifact

### Non-Negotiable

- Do NOT keep planning state only in chat. Persist it in Onward artifacts.
- Do NOT create ad-hoc todo lists, markdown checklists, or scratch planning files.
- Do NOT skip status updates. Every start, complete, and cancel must be recorded.
- If you discover work during execution, capture it as an Onward task IMMEDIATELY.
- At the end of every session, run `onward report` so the next agent (or human) can
  pick up exactly where you left off.
````

---

### Option B: SKILL.md File (Cursor Skills)

If your agent uses Cursor-style skills, create this as a skill file (e.g., `~/.cursor/skills/onward/SKILL.md` or within your project's skills directory).

````markdown
# Onward — Project Orchestration Skill

Use this skill for ALL planning, task decomposition, execution tracking, and status
management. Onward is the mandatory process manager for AI development in this workspace.

## When to Use

ALWAYS. Every work session. Every new initiative. Every task. If you're writing code in
this repo, you're using Onward to track it. There is no alternative workflow.

## Core Commands

```bash
# See the world
onward report --project <key>
onward next --project <key>
onward tree --project <key>
onward list --blocking --human

# Create work
onward new plan "<title>" --project <key>
onward new chunk PLAN-XXX "<title>"
onward new task CHUNK-XXX "<title>"
onward split PLAN-XXX
onward split CHUNK-XXX
onward review-plan PLAN-XXX

# Notes (scratch pad)
onward note <ID> "message"
onward note <ID>

# Move work forward
onward start <ID>
onward complete <ID>
onward cancel <ID>

# Inspect
onward show <ID>
onward progress
onward recent

# Optional: shared plan state (configure sync.mode in .onward.config.yaml)
onward sync status
onward sync push
onward sync pull
```

## The Operating Loop

1. `onward report --project <key>` — orient yourself
2. `onward next --project <key>` — select work
3. `onward start <ID>` — claim it
4. Execute the task
5. `onward complete <ID>` — mark done
6. If follow-up work was discovered: `onward new task <CHUNK-ID> "<title>"`
7. Return to step 1

## Rules

- NEVER maintain plans outside of Onward artifacts
- ALWAYS run `onward start` before beginning work and `onward complete` after
- ALWAYS capture discovered follow-up work as new Onward tasks immediately
- ALWAYS run `onward report` at end of session to leave breadcrumbs for the next agent
- Artifact files in `.onward/plans/` are the ONLY source of truth for project state
````

---

### Option C: System Prompt / SOUL.md Addition

For agents configured via system prompts, SOUL.md, or similar instruction files, add this block:

```
You MUST use Onward (the `onward` CLI) as your EXCLUSIVE system for planning, task
tracking, and execution management. All work is structured as Plan → Chunk → Task
artifacts stored in .onward/plans/.

MANDATORY BEHAVIORS:
- Start every session with `onward report` to understand current state
- Create plans via `onward new plan` before any significant work
- Decompose plans into chunks and tasks before implementation
- Run `onward start <ID>` before beginning any task
- Run `onward complete <ID>` after finishing any task
- Capture ALL discovered follow-up work as new tasks immediately
- End every session with `onward report` to preserve state for continuity
- NEVER maintain planning state in chat, scratch files, or memory alone

KEY COMMANDS: onward report, onward next, onward new, onward start, onward complete,
onward list, onward tree, onward show, onward split, onward review-plan, onward note,
onward sync (status|push|pull) when using branch/repo sync mode
```

---

### Option D: Quick-Reference Card (for any format)

If you need a minimal, dense reference to paste anywhere:

```
ONWARD QUICK-REF:
  report   → see everything          next     → what to do now
  new plan → start initiative         new chunk/task → decompose
  split    → AI-decompose             review-plan → adversarial review
  note     → scratch pad               start    → begin work
  complete → finish work              cancel   → abandon work
  list     → filter artifacts         tree     → hierarchy view
  show     → inspect one artifact     progress → what's in flight
  recent   → what just finished       archive  → retire a plan
  sync     → mirror .onward/plans to branch or second repo (optional)

WORKFLOW: report → next → start → work → complete → report (repeat forever)
FLAGS: --project <key>  --blocking  --human  --no-color
```

---

## Phase 3: First Run

Once your agent is configured, here's the exact sequence to start your first project:

```bash
# 1. Make sure the workspace is ready
onward doctor

# 2. Create your first plan
onward new plan "My First Feature" --project myproject

# 3. Look at what was created
onward show PLAN-001

# 4. Edit the plan file to fill in details
#    (the file path is shown by `onward show`)
#    Fill in: Summary, Goals, Proposed Approach, Acceptance Criteria

# 5. Decompose into chunks (manual or AI-assisted)
onward new chunk PLAN-001 "Backend implementation" --project myproject
onward new chunk PLAN-001 "Frontend integration" --project myproject

# 6. Decompose chunks into tasks
onward new task CHUNK-001 "Add database schema" --project myproject
onward new task CHUNK-001 "Implement API endpoints" --project myproject
onward new task CHUNK-002 "Build settings page" --project myproject

# 7. See the full picture
onward report --project myproject
onward tree --project myproject

# 8. Start working
onward next --project myproject
onward start TASK-001
# ... do the work ...
onward complete TASK-001

# 9. Check the dashboard
onward report --project myproject
```

That's it. You're on the rails. The train is moving. Keep it moving.

---

## Metadata Cheat Sheet

When creating or editing task frontmatter, these fields matter:

| Field | What it does | Example |
|---|---|---|
| `project` | Cross-plan grouping and filtering | `project: auth-rewrite` |
| `human` | Flags tasks requiring a person | `human: true` |
| `blocked_by` | Dependency tracking | `blocked_by: [TASK-003]` |
| `block_reason` | Why it's stuck | `block_reason: Waiting on API decision` |
| `status` | Current state | `open`, `in_progress`, `completed`, `canceled` |

### The Blocking Pattern

When an agent hits a wall that requires human input:

```bash
onward new task CHUNK-001 "Decide on auth token format" --project myproject
# Then edit the task's frontmatter to add:
#   human: true
#   block_reason: "Need architecture decision from team"
```

Then any agent (or human) can find these with:

```bash
onward list --blocking --human
```

---

## Configuration Reference

Onward's workspace config lives at `.onward.config.yaml` in your project root. Key sections:

```yaml
version: 1

# Root directory for all Onward artifacts.
path: .onward

sync:
  mode: local              # local | branch | repo
  branch: onward           # used when mode is branch (git worktree on this branch)
  repo: null               # clone URL or path when mode is repo
  worktree_path: .onward/sync   # sync checkout directory (gitignored)

ralph:
  command: ralph
  enabled: true

models:
  default: opus-latest           # fallback for everything
  task_default: sonnet-latest    # default for new tasks
  split_default:                 # blank = use default
  review_default: codex-latest   # review hooks/workflows

review:
  double_review: true            # two independent reviewers (review_default + default)

work:
  sequential_by_default: true
  create_worktree: true
  base_branch: main

hooks:
  post_task_markdown: .onward/hooks/post-task.md
  post_chunk_markdown: .onward/hooks/post-chunk.md
```

With `sync.mode` set to `branch` or `repo`, use:

```bash
onward sync status   # clean/dirty vs remote (or “not initialized” until first push)
onward sync push     # copy plans → sync checkout, commit, push
onward sync pull     # fast-forward sync checkout, copy plans → workspace, reindex
```

`onward doctor` validates the `sync:` section (for example, branch mode requires a git repo at the workspace root).

### Plan sync semantics (branch and repo modes)

- **Mirror** — After each push or pull direction, the destination `.onward/plans/` tree matches the source (files absent on the source are removed on the destination).
- **First run** — `onward sync status` does not clone or add a worktree; it reports that the sync checkout is not initialized until the first successful **`onward sync push`**.
- **Push** — Copies from your workspace into the sync checkout, commits under `.onward/plans` when there are changes, then runs **`git push -u origin HEAD`**. The sync checkout must have **`origin`** set; the remote should allow the update (a **bare** repository is the usual choice for `repo` mode).
- **Pull** — Runs **`git pull --ff-only`** in the sync checkout (non-fast-forward updates fail with an error until you reconcile in that checkout), copies plans into the workspace, then regenerates **`index.yaml`** / **`recent.yaml`**.

### Model Aliases

Onward supports short aliases so you don't have to remember full model identifiers.
Use `<family>-latest` to always get the current best version of a model family:

| Alias | Resolves to |
|---|---|
| `opus-latest` or `opus` | `claude-opus-4-6` |
| `sonnet-latest` or `sonnet` | `claude-sonnet-4-6` |
| `haiku-latest` or `haiku` | `claude-haiku-4` |
| `codex-latest` or `codex` | `codex-5-3` |
| `gpt5` | `gpt-5` |

You can also use full model identifiers directly (e.g., `claude-opus-4-6`). Aliases are resolved
at execution time, so updating Onward automatically picks up new model versions.

---

## Troubleshooting

**"Not an Onward workspace"** — Run `onward init` in your project root, or pass `--root /path/to/workspace`.

**Commands work but agent isn't using Onward** — Your agent configuration (AGENTS.md, SKILL.md, system prompt) is missing or the Onward instructions aren't prominent enough. Move them to the TOP of the file. Agents read top-down and prioritize early instructions.

**Plans feel too big** — Use `onward split` to AI-decompose plans into chunks and chunks into tasks. The goal is tasks small enough that one agent can finish in one session.

**Lost track of what's happening** — `onward report` is your friend. Run it early, run it often, run it at the end of every session.

**`onward sync push` fails at `git push`** — Ensure the sync worktree has `git remote -v` showing `origin`, and that the remote accepts pushes to that branch. For a local test remote, use **`git init --bare`**. Pushing to another machine’s **non-bare** repo often fails if that repo has the same branch checked out.

**`onward sync pull` fails on `git pull --ff-only`** — Someone advanced the remote history in a non-fast-forward way. Open the sync checkout at `sync.worktree_path`, run `git status` / `git log`, merge or rebase as you prefer, then retry **`onward sync pull`**.

**`Doctor found issues` mentioning `sync.`** — Fix `.onward.config.yaml`: in **`branch`** mode the workspace root must be a git working tree; in **`repo`** mode set `sync.repo` to your clone URL or path.

---

*Structure is freedom. Plans are memory. The train doesn't stop. Move onward.*
