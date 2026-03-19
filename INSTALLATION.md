# Installation and Agent Setup

This document covers two things:

1. Installing Trains locally.
2. Setting up an agent (for example OpenClaw) so all work is tracked through Trains artifacts.

## 1. Install Trains (CLI usage from anywhere)

From repo root:

```bash
python3.11 -m pip install -e .
trains --help
```

Optional test tooling:

```bash
python3.11 -m pip install -e '.[dev]'
pytest
```

Behavior note:

- `trains init` works in any directory and bootstraps a workspace there.
- All other commands require a valid Trains workspace root and will exit if missing.
- The error message explicitly recommends `trains init`.

If `pytest` is unavailable, run fallback checks:

```bash
./scripts/test.sh
```

## 2. Dogfood consumer workspace (recommended)

```bash
./scripts/dogfood/bootstrap.sh
./scripts/dogfood/e2e.sh
```

This creates `.dogfood/consumer-app` and wires a local `trains` command in that venv.

## 3. Agent operating policy (important)

To keep planning state reliable, the agent should follow these rules:

1. Every substantial workstream starts with `trains new plan`.
2. Work is decomposed into chunk/task artifacts before implementation.
3. Any discovered blocker/refactor/follow-up is immediately captured as a new task.
4. Use metadata consistently:
   - `blocked_by` when a task waits on another task
   - `human: true` when a person must do it
   - `project: <key>` for cross-plan filtering
5. Before ending a run, update status using `start`, `complete`, or `cancel`.

## 4. Suggested parent-agent loop

Use this loop for OpenClaw-like supervisors:

```bash
trains report --project <key>
trains next --project <key>
# dispatch selected work
trains report --project <key>
```

Use focused filters for unblock triage:

```bash
trains list --project <key> --blocking --human
```

## 5. Suggested system prompt additions for your agent

Add guidance like:

- "When user describes a new initiative, create a plan via `trains new plan` and then fill the generated template file."
- "Do not keep planning state only in chat. Persist it in `.train/plans/...` artifacts."
- "If you discover follow-up work during execution, create a task artifact immediately with `blocked_by`, `human`, and `project` fields when known."
- "At the end of each execution loop, update artifact status and run `trains report`."

## 6. First commands for a new project

```bash
trains new plan "<title>" --project <key>
trains show PLAN-001
# fill plan template sections
trains new chunk PLAN-001 "<chunk title>" --project <key>
trains new task CHUNK-001 "<task title>" --project <key>
trains report --project <key>
```
