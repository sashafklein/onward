# Onward Contributor Guide

This guide is for first-time contributors who want to run Onward locally without guessing.

## 1. What Onward is (today)

Right now this repo supports:

- workspace bootstrap (`onward init`)
- structural validation (`onward doctor`, including `sync:` config checks)
- artifact creation (`onward new plan`, `onward new chunk`, `onward new task`)
- decomposition via `onward split` (executor-backed by default; **`--heuristic`** for markdown-only; `TRAIN_SPLIT_RESPONSE` env for tests — see [CAPABILITIES.md](CAPABILITIES.md))
- adversarial plan review (`onward review-plan` with configurable single/double reviewer)
- artifact discovery (`onward list` with `--project`, `--blocking`, `--human`)
- active work tree (`onward tree` with `--project`; omits completed/canceled chunks and tasks; task lines show `(A)` agent vs `(H)` human — see `onward tree --help`)
- roadmap view (`onward roadmap` — incomplete plans with summaries and chunks)
- consolidated status (`onward report`; same task markers plus `[Blocking Human Tasks]` — see `onward report --help`)
- artifact inspection (`onward show <ID>` — tasks include latest run info)
- per-artifact notes (`onward note <ID> ["message"]`)
- state transitions (`onward complete`, `onward cancel`, `onward retry`) and executor-driven status from `onward work` — see [LIFECYCLE.md](LIFECYCLE.md)
- task/chunk execution handoff (`onward work` — passes full chunk/plan context to executor, dependency-aware chunk execution, pre/post hooks)
- active/completed views (`onward progress`, `onward recent` — recent includes run records)
- next-item suggestion (`onward next`) and full ready-task listing (`onward ready`)
- plan archival (`onward archive PLAN-###`)
- artifact root migration (`onward migrate` — moves artifacts when `root` config changes)
- optional plan sync (`onward sync status`, `onward sync push`, `onward sync pull` when `sync.mode` is `branch` or `repo`)

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

Install in editable mode from the repo root:

```bash
pip install -e .
```

Then verify:

```bash
onward init
onward doctor
onward list
```

> **Running from source without installing?** Prefix every command with `PYTHONPATH=src python3 -m onward.cli` instead of `onward` (e.g. `PYTHONPATH=src python3 -m onward.cli init`).

Expected behavior:

- `init` creates `.onward.config.yaml`, `.onward/`, and default templates/indexes.
- `doctor` prints `Doctor check passed`.
- `list` may print `No artifacts found` if you have not created any yet.

Create your first artifacts:

```bash
onward new plan "First Plan" --description "learning flow"
onward new chunk PLAN-001 "First Chunk"
onward new task CHUNK-001 "First Task"
onward list
onward show TASK-001
onward list --blocking --human
onward report --no-color
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

```bash
pip install -e '.[dev]'
pytest
```

> If you haven't installed in editable mode, use `PYTHONPATH=src python3 -m pytest` instead.

Test coverage currently includes:

- init/doctor success and failure paths (including invalid `sync` settings)
- plan/chunk/task creation flows
- list/show behavior (including latest run info for tasks)
- duplicate ID detection
- frontmatter parser/serializer round-trip behavior
- split: dry-run, plan-to-chunks, chunk-to-tasks, invalid JSON, validation errors, collision detection, deterministic IDs, executor payload, `--force`, dependency cycles
- work: task success/failure lifecycle, chunk sequential execution with dependency ordering, shell/markdown hooks, executor payload enrichment (chunk + plan context)
- recent: includes both completed artifacts and terminal run records
- review-plan: single and double reviewer flows
- notes: add, view, surfacing on completion
- sync: local status, branch push with bare `origin`, repo push/pull, doctor + branch mode without git
- onboarding simulation: fresh `init` → `doctor` → `new plan/chunk/task` → `next` / `report` → `work` with executor `true` ([`tests/test_onboarding_simulation.py`](../tests/test_onboarding_simulation.py))

Convenience runner:

```bash
./scripts/test.sh
```

This runs pytest when available, otherwise it runs dogfood e2e smoke checks.

### Architecture / seam tests

[`tests/test_architecture_seams.py`](../tests/test_architecture_seams.py) encodes boundaries that are easy to regress:

- Default `.onward.config.yaml` in [`src/onward/scaffold.py`](../src/onward/scaffold.py) must parse and pass `validate_config_contract_issues` (same rules as `onward doctor`), and every key must appear in `CONFIG_TOP_LEVEL_KEYS` / `CONFIG_SECTION_KEYS` in [`src/onward/config.py`](../src/onward/config.py).
- [`src/onward/cli.py`](../src/onward/cli.py) may only import from `onward.cli_commands` and `onward.scaffold` (thin entrypoint).
- No `from onward… import _leading_underscore` anywhere under `src/onward/` (public cross-module APIs only; see PLAN-010 TASK-012).
- [`docs/schemas/onward-executor-stdin-v1.schema.json`](../docs/schemas/onward-executor-stdin-v1.schema.json) must stay valid JSON, keep `schema_version` consts aligned with `EXECUTOR_PAYLOAD_SCHEMA_VERSION`, and keep `required` arrays in sync with the frozensets in [`src/onward/executor_payload.py`](../src/onward/executor_payload.py).

[`tests/test_docs_consistency.py`](../tests/test_docs_consistency.py) requires **README.md**, **INSTALLATION.md**, and **this guide** each to mention every leaf `onward …` subcommand from `build_parser()` (so `a|b|c` shorthand alone is not enough).

Executor **preflight** (PATH / executable file for `executor.command`) lives in [`src/onward/preflight.py`](../src/onward/preflight.py) and is covered by [`tests/test_preflight.py`](../tests/test_preflight.py).

When you add config keys, new subcommands, or change executor stdin, update the allowlists / schema / payload module **and** extend or adjust these tests if the contract changes.

### Docs consistency (local)

```bash
pytest tests/test_docs_consistency.py -v
```

This is included in the full suite (`./scripts/test.sh` / `pytest`).

### Manual checklist (releases & deep doc drift)

Automation does not cover everything. Before a release or large doc reshuffle, skim:

- **[CAPABILITIES.md](CAPABILITIES.md)** — model-backed vs local commands still match [`build_parser()`](../../src/onward/cli.py) and executor behavior.
- **INSTALLATION.md** — pasted agent blocks (e.g. `AGENTS.md` excerpt) stay aligned with this repo’s **AGENTS.md** where they are meant to match.
- **[FORMAT_MIGRATION.md](FORMAT_MIGRATION.md)** / executor schema — if `EXECUTOR_PAYLOAD_SCHEMA_VERSION` or `docs/schemas/onward-executor-stdin-v1.schema.json` changed, migration notes and consumers are updated.
- **Version** — `pyproject.toml` / tag / changelog if you publish a release artifact.

## 6. Common errors and fixes

### `No module named onward`

You haven't installed the package. Either install it:

```bash
pip install -e .
onward --help
```

Or run from source:

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
- **[AI_OPERATOR.md](AI_OPERATOR.md)** — operator quickstart, anti-patterns, recovery playbooks
- **`.onward/plans/`** — active plans and tasks; use `onward report` for orientation
- **[LIFECYCLE.md](LIFECYCLE.md)** — `work` / `complete` / `cancel` / `retry` rules
- **[CAPABILITIES.md](CAPABILITIES.md)** — model-backed vs local commands
- **[WORK_HANDOFF.md](WORK_HANDOFF.md)** — how `onward work` and executor handoff fit together
- **[archive/PROVIDER_REGISTRY.md](archive/PROVIDER_REGISTRY.md)** — archived: multi-provider routing design (superseded by executor layer)
