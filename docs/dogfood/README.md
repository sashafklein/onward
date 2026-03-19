# Dogfood Workflow

The dogfood workspace lives at `.dogfood/consumer-app` (gitignored).

Bootstrap:

```bash
./scripts/dogfood/bootstrap.sh
```

The bootstrap does this:

1. Creates `.dogfood/consumer-app`.
2. Initializes a git repo in that consumer workspace.
3. Creates a local Python venv there.
4. Links this repo's `src/` into that venv via a `.pth` file.
5. Creates a `train` executable in the venv (`python -m trains.cli`).
6. Runs `train init --root .dogfood/consumer-app`.
7. Seeds a first plan if the workspace has none.

Typical loop:

```bash
source .dogfood/consumer-app/.venv/bin/activate
train list --root .dogfood/consumer-app
train new --root .dogfood/consumer-app chunk PLAN-001 "Implement parser"
train new --root .dogfood/consumer-app task CHUNK-001 "Handle list fields"
train show --root .dogfood/consumer-app TASK-001
```

End-to-end verification:

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
