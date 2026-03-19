# Onward

Onward is a git-native CLI for planning and driving AI-enabled development work with markdown-first artifacts.

Current state: scaffold + core artifact commands (`init`, `doctor`, `new`, `list`, `show`, `start`, `complete`, `cancel`, `progress`, `recent`, `next`, `report`, `archive`) + dogfood workspace tooling + automated tests.

## Install (CLI from anywhere)

```bash
python3.11 -m pip install -e .
```

Then use `onward` from any shell location:

```bash
onward --help
```

If your current directory is not an Onward workspace, non-`init` commands fail with guidance to run:

```bash
onward init
```

## Quickstart

```bash
onward init
onward doctor
```

## Repository Layout

- `.onward.config.yaml` root config.
- `.onward/plans/` tracked planning artifacts (`plan/chunk/task`) and derived indexes.
- `.onward/templates/` artifact body templates.
- `.onward/hooks/` markdown hooks.
- `.onward/sync/` sync workspace state.
- `.onward/runs/` and `.onward/ongoing.json` runtime state (gitignored).

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
- Product spec: [docs/spec/onward_v1_product_spec.md](/Users/sasha/code/train/docs/spec/onward_v1_product_spec.md)

## Useful Commands

```bash
onward list --project alpha
onward list --blocking --human
onward next --project alpha
onward tree --project alpha
onward report --project alpha
```

## Documented Next Features

The spec now explicitly captures upcoming requirements for:

- feedback-loop task capture during execution (blockers/refactors/for-later)
- task metadata: `blocked_by`, `human`, optional `project`
- focused blocking views (for example `onward list --blocking --human`)
- rich terminal overview via `onward report`
