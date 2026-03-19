# Trains

Trains is a git-native CLI for planning and driving AI-enabled development work with markdown-first artifacts.

Current state: scaffold + core artifact commands (`init`, `doctor`, `new`, `list`, `show`, `start`, `complete`, `cancel`, `progress`, `recent`, `next`, `report`, `archive`) + dogfood workspace tooling + automated tests.

## Install (CLI from anywhere)

```bash
python3.11 -m pip install -e .
```

Then use `trains` from any shell location:

```bash
trains --help
```

If your current directory is not a Trains workspace, non-`init` commands fail with guidance to run:

```bash
trains init
```

## Quickstart

```bash
trains init
trains doctor
```

## Repository Layout

- `.train.config.yaml` root config.
- `.train/plans/` tracked planning artifacts (`plan/chunk/task`) and derived indexes.
- `.train/templates/` artifact body templates.
- `.train/hooks/` markdown hooks.
- `.train/sync/` sync workspace state.
- `.train/runs/` and `.train/ongoing.json` runtime state (gitignored).

## Dogfood

Bootstrap a local consumer workspace that uses this repo as the source package:

```bash
./scripts/dogfood/bootstrap.sh
```

Run end-to-end verification of the dogfood flow:

```bash
./scripts/dogfood/e2e.sh
```

## Testing

If you have `pytest` installed:

```bash
PYTHONPATH=src python3 -m pytest
```

Or install test dependencies first:

```bash
pip install -e .[dev]
PYTHONPATH=src python3 -m pytest
```

One-command test runner (falls back to dogfood e2e if `pytest` is unavailable):

```bash
./scripts/test.sh
```

## Documentation

- Installation + agent setup: [INSTALLATION.md](/Users/sasha/code/train/INSTALLATION.md)
- New contributor walkthrough: [docs/NOOB_GUIDE.md](/Users/sasha/code/train/docs/NOOB_GUIDE.md)
- Dogfood workflow: [docs/dogfood/README.md](/Users/sasha/code/train/docs/dogfood/README.md)
- Work handoff design: [docs/architecture/work-handoff.md](/Users/sasha/code/train/docs/architecture/work-handoff.md)
- Product spec: [docs/spec/train_v1_product_spec.md](/Users/sasha/code/train/docs/spec/train_v1_product_spec.md)

## Useful Commands

```bash
trains list --project alpha
trains list --blocking --human
trains next --project alpha
trains tree --project alpha
trains report --project alpha
```

## Documented Next Features

The spec now explicitly captures upcoming requirements for:

- feedback-loop task capture during execution (blockers/refactors/for-later)
- task metadata: `blocked_by`, `human`, optional `project`
- focused blocking views (for example `train list --blocking --human`)
- rich terminal overview via `train report`
