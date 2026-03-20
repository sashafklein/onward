# Agent Instructions for Onward Development

You are working on **Onward** itself — the git-native planning and execution CLI for AI-driven development.

## Onward — Mandatory Project Orchestration

**CRITICAL: ALL planning, task tracking, and execution management in this repository
MUST go through Onward.** Do not maintain plans in chat, in comments, in scratch files,
or in your own memory. Onward is the single source of truth. Yes, even when developing
Onward itself. We eat our own cooking.

### The Rule

Every piece of work — from initial planning through final completion — is tracked as an
Onward artifact. No exceptions. If it's not in `.onward/plans/`, it doesn't exist.

### The Loop

This is your operating rhythm. Follow it relentlessly:

```
onward report                 ← See the full picture
onward next                   ← Pick the next thing
onward start <ID>             ← Optional: mark in_progress (claim / visibility)
onward work <TASK-ID|CHUNK-ID|PLAN-ID>  ← Run executor (task / chunk / whole plan); on success tasks complete
onward report                 ← Hand off to the next session or agent
```

Use **`onward complete <ID>`** when you finish work **without** running `onward work` (e.g. closure outside the executor). After a **successful** `onward work`, do not run `complete` on the same task — it is already **`completed`**.

Authoritative rules: **[docs/LIFECYCLE.md](docs/LIFECYCLE.md)**.

### Starting New Work

When the user describes a new initiative, feature, or project:

1. `onward new plan "<title>"` — create the plan artifact
2. Edit the generated plan.md — fill in Summary, Goals, Proposed Approach, Acceptance Criteria
3. `onward split PLAN-XXX` or manually create chunks with `onward new chunk`
4. `onward split CHUNK-XXX` or manually create tasks with `onward new task`
5. `onward report` — confirm the work is structured

### During Execution

- Prefer **`onward work <TASK-ID>`** for executor-backed runs; it updates status and writes run records.
- Run **`onward start <ID>`** when you want the artifact **`in_progress`** before other steps (optional if you go straight to `work`).
- Run **`onward complete <ID>`** only when closing a task **without** `work`, or for artifacts that never use `work`.
- If you discover follow-up work, blockers, or refactors: IMMEDIATELY create a new task
  with `onward new task <CHUNK-ID> "<title>"` and set `blocked_by`, `human`, and `project`
  metadata in the frontmatter as appropriate
- Run `onward report` at the end of every work session to leave a clear picture for the
  next session or the next agent
- If this workspace uses `sync.mode: branch` or `repo` in `.onward.config.yaml`, use
  `onward sync status`, `onward sync push`, and `onward sync pull` as needed so plan
  files stay aligned with the configured remote checkout (see README / INSTALLATION.md).

### Non-Negotiable

- Do NOT keep planning state only in chat. Persist it in Onward artifacts.
- Do NOT create ad-hoc todo lists, markdown checklists, or scratch planning files.
- Do NOT leave work in a misleading status: use **`work`**, **`complete`**, or **`cancel`** as appropriate so `report` / `next` stay truthful.
- If you discover work during execution, capture it as an Onward task IMMEDIATELY.
- At the end of every session, run `onward report` so the next agent (or human) can
  pick up exactly where you left off.

## Codebase Notes

- Source lives in `src/onward/` (`cli.py` + `cli_commands.py` for handlers, plus `artifacts.py`, `execution.py`, `sync.py`, `preflight.py`, `executor_ack.py`, `executor_payload.py`, …)
- Tests are in `tests/` — run with `pytest` or `./scripts/test.sh`
- The package is `onward-cli`, installed via `pip install -e .`
- Entry point: `onward` command (maps to `onward.cli:main`)
- Python 3.11+ required
- Templates, hooks, and prompts live in `.onward/templates/`, `.onward/hooks/`, `.onward/prompts/`
- Contributor guide: `docs/CONTRIBUTION.md`
- Planning / roadmap: `.onward/plans/` (run `onward report` for current work)
