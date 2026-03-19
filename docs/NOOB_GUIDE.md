# Onward Noob Guide

This guide is for first-time contributors who want to run Onward locally without guessing.

## 1. What Onward is (today)

Right now this repo supports:

- workspace bootstrap (`onward init`)
- structural validation (`onward doctor`)
- artifact creation (`onward new plan|chunk|task`)
- artifact discovery (`onward list`)
- artifact inspection (`onward show <ID>`)
- state transitions (`onward start|complete|cancel`)
- active/completed views (`onward progress`, `onward recent`)
- next-item suggestion (`onward next`)
- consolidated status dashboard (`onward report`)
- plan archival (`onward archive PLAN-###`)

Onward stores tracked planning state in `.onward/plans/` and runtime state in `.onward/`.

## 2. Prerequisites

- macOS/Linux shell
- Python 3.11+ recommended
- git

Check Python:

```bash
python3 --version
```

## 3. First 10 minutes

From repo root:

```bash
PYTHONPATH=src python3 -m onward.cli init
PYTHONPATH=src python3 -m onward.cli doctor
PYTHONPATH=src python3 -m onward.cli list
```

Expected behavior:

- `init` creates `.onward.config.yaml`, `.onward/`, and default templates/indexes.
- `doctor` prints `Doctor check passed`.
- `list` may print `No artifacts found` if you have not created any yet.

Create your first artifacts:

```bash
PYTHONPATH=src python3 -m onward.cli new plan "First Plan" --description "learning flow"
PYTHONPATH=src python3 -m onward.cli new chunk PLAN-001 "First Chunk"
PYTHONPATH=src python3 -m onward.cli new task CHUNK-001 "First Task"
PYTHONPATH=src python3 -m onward.cli list
PYTHONPATH=src python3 -m onward.cli show TASK-001
PYTHONPATH=src python3 -m onward.cli list --blocking --human
PYTHONPATH=src python3 -m onward.cli report --no-color
```

## 4. Dogfood workflow

Use the local consumer app flow for realistic testing:

```bash
./scripts/dogfood/bootstrap.sh
./scripts/dogfood/e2e.sh
```

What this does:

- creates `.dogfood/consumer-app` (gitignored)
- creates a venv there
- links this repo's `src/` into that venv
- runs Onward commands in a consumer-style workspace
- validates an end-to-end flow with assertions

## 5. Automated tests

### Option A: pytest already available

```bash
PYTHONPATH=src python3 -m pytest
```

### Option B: install dev deps first

```bash
pip install -e .[dev]
PYTHONPATH=src python3 -m pytest
```

Test coverage currently includes:

- init/doctor success and failure paths
- plan/chunk/task creation flows
- list/show behavior
- duplicate ID detection
- frontmatter parser/serializer round-trip behavior

Convenience runner:

```bash
./scripts/test.sh
```

This runs pytest when available, otherwise it runs dogfood e2e smoke checks.

## 6. Common errors and fixes

### `No module named onward`

You are missing `PYTHONPATH=src` for direct module execution.

Use:

```bash
PYTHONPATH=src python3 -m onward.cli --help
```

### `onward: command not found` in dogfood workspace

Activate the dogfood venv first:

```bash
source .dogfood/consumer-app/.venv/bin/activate
```

### `Error: plan not found: PLAN-###`

You are trying to create a chunk under a plan ID that does not exist in this root.

Check:

```bash
onward list --root <workspace> --type plan
```

### `Error: chunk not found: CHUNK-###`

Same issue, but for task creation. Verify chunk IDs first.

### `Doctor found issues`

Run `onward init --root <workspace>` once, then rerun doctor.

If the issue mentions invalid JSON in `.onward/ongoing.json`, replace it with valid JSON or re-run init with `--force`.

## 7. Rules of thumb

- Always pass `--root` when working outside repo root.
- Treat `.onward/plans/` as source of truth.
- Treat `.onward/plans/index.yaml` and `recent.yaml` as derived files.
- Keep frontmatter simple; complex YAML nesting is intentionally unsupported right now.

## 8. Upcoming workflow features (documented)

The product spec includes planned additions for:

- execution-time follow-up capture (workers adding blocker/refactor/for-later tasks)
- `human: true|false` task metadata for explicit human-required work
- optional `project` metadata for cross-plan filtering
- blocking/human-focused list filters (for example `onward list --blocking --human`)
- `onward report` for a unified colorized ASCII status dashboard
