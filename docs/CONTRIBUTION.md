# Onward Noob Guide

This guide is for first-time contributors who want to run Onward locally without guessing.

## 1. What Onward is (today)

Right now this repo supports:

- workspace bootstrap (`onward init`)
- structural validation (`onward doctor`, including `sync:` config checks)
- artifact creation (`onward new plan|chunk|task`)
- AI-assisted decomposition (`onward split` for plans and chunks, with heuristic fallback and `TRAIN_SPLIT_RESPONSE` override for testing)
- adversarial plan review (`onward review-plan` with configurable single/double reviewer)
- artifact discovery (`onward list` with `--project`, `--blocking`, `--human`)
- artifact inspection (`onward show <ID>` — tasks include latest run info)
- per-artifact notes (`onward note <ID> ["message"]`)
- state transitions (`onward start|complete|cancel`) and executor-driven status from `onward work` — see [LIFECYCLE.md](LIFECYCLE.md)
- task/chunk execution handoff (`onward work` — passes full chunk/plan context to executor, dependency-aware chunk execution, pre/post hooks)
- active/completed views (`onward progress`, `onward recent` — recent includes run records)
- next-item suggestion (`onward next`)
- consolidated status dashboard (`onward report`)
- plan archival (`onward archive PLAN-###`)
- optional plan sync (`onward sync status|push|pull` when `sync.mode` is `branch` or `repo`)

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

- init/doctor success and failure paths (including invalid `sync` settings)
- plan/chunk/task creation flows
- list/show behavior (including latest run info for tasks)
- duplicate ID detection
- frontmatter parser/serializer round-trip behavior
- split: dry-run, plan-to-chunks, chunk-to-tasks, invalid JSON, validation errors, collision detection, deterministic IDs
- work: task success/failure lifecycle, chunk sequential execution with dependency ordering, shell/markdown hooks, executor payload enrichment (chunk + plan context)
- recent: includes both completed artifacts and terminal run records
- review-plan: single and double reviewer flows
- notes: add, view, surfacing on completion
- sync: local status, branch push with bare `origin`, repo push/pull, doctor + branch mode without git

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

If the issue mentions **`sync.`** (for example branch mode without `.git`), fix `.onward.config.yaml` or initialize a git repository at the workspace root. See [INSTALLATION.md](../INSTALLATION.md) (Configuration Reference → sync).

### Plan sync (`onward sync`)

Only relevant when `sync.mode` is **`branch`** (git worktree on another branch in the same repo) or **`repo`** (clone of another repository). Default **`local`** mode does not use a sync target.

```bash
onward sync status   # clean/dirty vs remote tree, or "not initialized" until first push
onward sync push     # mirror .onward/plans → sync checkout, commit, git push
onward sync pull     # git pull --ff-only in checkout, mirror → workspace, reindex
```

The sync checkout lives under `sync.worktree_path` (default `.onward/sync/`, gitignored). See README and INSTALLATION for push/pull requirements (`origin`, bare remote, fast-forward pull).

## 7. Rules of thumb

- Always pass `--root` when working outside repo root.
- Treat `.onward/plans/` as source of truth.
- Treat `.onward/plans/index.yaml` and `recent.yaml` as derived files.
- Keep frontmatter simple; complex YAML nesting is intentionally unsupported right now.

## 8. Deeper reference

- **[INSTALLATION.md](../INSTALLATION.md)** — agent setup, full config reference, sync semantics and troubleshooting
- **`.onward/plans/`** — active plans and tasks; use `onward report` for orientation
- **[WORK_HANDOFF.md](WORK_HANDOFF.md)** — how `onward work` and executor handoff fit together
