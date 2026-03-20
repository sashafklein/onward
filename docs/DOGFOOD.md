# Dogfood Workflow

The dogfood workspace lives at `.dogfood/consumer-app` (gitignored).

## Requirements

- **Python 3.11+** on your PATH. The bootstrap script tries, in order: `python3.13`, `python3.12`, `python3.11`, then `python3`. If none is 3.11+, bootstrap exits with an error.

## Bootstrap

```bash
./scripts/dogfood/bootstrap.sh
```

The bootstrap does this:

1. Creates `.dogfood/consumer-app`.
2. Initializes a git repo in that consumer workspace (if missing).
3. Creates or **recreates** a local Python venv there if the existing venv is missing or older than Python 3.11.
4. Links this repo's `src/` into that venv via a `.pth` file.
5. Installs an `onward` launcher in the venv that always runs `python -m onward.cli` using **that venv’s interpreter** (works even when `python` on your shell PATH is different).
6. Runs **`onward init --root .dogfood/consumer-app`** so the tree (`.onward/`, `.onward.config.yaml`, templates, indexes) exists every time — no separate manual init step.
7. Runs **`onward doctor --root`** and fails fast if the workspace is invalid.
8. Seeds a first plan if the workspace has none.

Re-running bootstrap is **idempotent**: an existing 3.11+ venv is reused; git is not re-initialized; `onward init` skips overwriting existing scaffold files unless you use `onward init --force` yourself.

## Typical loop

```bash
source .dogfood/consumer-app/.venv/bin/activate
onward list --root .dogfood/consumer-app
onward new --root .dogfood/consumer-app chunk PLAN-001 "Implement parser"
onward new --root .dogfood/consumer-app task CHUNK-001 "Handle list fields"
onward show --root .dogfood/consumer-app TASK-001
```

## End-to-end verification

From repo root (uses the same bootstrap + venv rules):

```bash
./scripts/dogfood/e2e.sh
```

Expected terminal tail:

```txt
[e2e] doctor
[e2e] create chunk + task
[e2e] list
[e2e] show
[e2e] PASS
```

**Full procedure:** clone repo → run `./scripts/dogfood/e2e.sh` (which runs bootstrap) → no extra `onward init` is required.
