# Provider registry (design)

**Status:** design only — default behavior today is unchanged: a single executor (`ralph.command` + `ralph.args`) receives a resolved model string on stdin; [`config.py`](../src/onward/config.py) maps aliases like `sonnet-latest` via `MODEL_FAMILIES` / `resolve_model_alias`. This document specifies how **explicit multi-provider routing** could layer on without breaking that path.

**Related:** [CAPABILITIES.md](CAPABILITIES.md) (`review.reviewers` matrix + fallbacks), [WORK_HANDOFF.md](WORK_HANDOFF.md), PLAN-010 CHUNK-007 (TASK-019 — preflight, TASK-021 — review-plan provider selection, TASK-020 — execution contract).

---

## Problem

Model strings in artifacts and config (e.g. `opus-latest`, `claude-opus-4-6`, `gpt-5`) must eventually map to **different concrete backends**: OpenClaw, Claude CLI, Cursor agent CLI, Codex CLI, etc. Today everything is assumed to be handled by one `ralph` invocation; the executor is responsible for interpretation.

We want:

1. **Explicit routing** in config (no silent mis-routing when two CLIs are installed).
2. **Stable resolution rules** so agents can reason from docs alone.
3. **Opt-in** rollout — workspaces without new keys behave exactly as they do now.

---

## Feature flag (staged rollout)

```yaml
# Proposed (not implemented until code lands).
provider_registry:
  enabled: false   # default: off; entire block may be omitted
```

When `enabled` is false or the block is absent:

- Ignore all `providers` / per-provider tables below.
- Keep using `ralph` + `resolve_model_alias` only (current behavior).

When `enabled` is true:

- Require well-formed `providers` (see validation rules in a future `onward doctor` check).
- Resolve each executor-backed call to a **provider id** + **provider-native model id** before spawn.

---

## Config shape (proposal)

### Top-level keys (future)

| Key | Purpose |
| --- | ------- |
| `provider_registry` | `enabled`, optional defaults |
| `providers` | Named backend definitions |
| `models.routing` *(optional)* | Map logical alias → `{ provider, model }` |

Existing `models.default`, `task_default`, `split_default`, `review_default` remain; they continue to hold **logical** model names until routing runs.

### `providers` entry (sketch)

Each provider is a named backend:

```yaml
providers:
  claude_cli:
    kind: subprocess           # future: http, grpc, …
    command: claude
    args_prefix: []            # e.g. ["--print"] — executor-specific
    # Optional env or cwd hooks reserved for later tasks.

  openclaw:
    kind: subprocess
    command: openclaw
    args_prefix: ["run", "model"]

  cursor_agent:
    kind: subprocess
    command: cursor-agent
    args_prefix: []
```

**Open design point:** whether stdin JSON shape stays identical for all providers (preferred for v1) or each `kind` gets a thin adapter in Onward — implementation tasks should pick one and document it in [WORK_HANDOFF.md](WORK_HANDOFF.md).

### Per-command defaults (optional)

```yaml
provider_registry:
  enabled: true
  default_provider: claude_cli
  commands:
    work:
      provider: claude_cli
    review_plan:
      provider: openclaw
    split:
      provider: null           # null = no provider override; split stays heuristic unless future model-backed split uses executor
```

`split` today is heuristic ([CAPABILITIES.md](CAPABILITIES.md)); any future model-backed split would use the `split` override when set.

Hooks that invoke the executor (`pre_task_markdown`, etc.) inherit the **same provider resolution as `onward work`** for that task unless a hook-specific override is added later (out of scope for this design).

---

## Resolution order

For a given **executor-backed** operation, resolve **logical model** `M` and **provider** `P` in this order:

1. **Artifact / invocation model** — e.g. task frontmatter `model`, or `onward split --model`, or review’s configured reviewer model.
2. **Per-command override** — `provider_registry.commands.<command>.provider` when non-null (does not replace `M`, only chooses backend if the design ties provider to command first; see note below).
3. **Routing table** — if `models.routing` maps `M` (after normalizing case/`_`/`-`) to `{ provider, model }`, use that pair as the effective `(P, M_native)`.
4. **`resolve_model_alias(M)`** — existing [`resolve_model_alias`](../src/onward/config.py) expands `-latest` and family shorthands to canonical strings (still logical, not necessarily native IDs).
5. **Default provider** — `provider_registry.default_provider` when enabled; if still unset, fall back to legacy single-executor behavior: `ralph` only.

**Note:** Step 2 vs 3 ordering is the main ambiguity. Implementation should choose **one** documented order; recommended: apply **routing table on logical name first** (steps 1 → 4), then **command default provider** only when routing did not set `P`, then **default_provider**, then **ralph** fallback.

Document the final order in code comments and [CAPABILITIES.md](CAPABILITIES.md) when implemented.

---

## Doctor / contract (future)

When `provider_registry.enabled` is true:

- Every `providers.*` entry must have `kind`, `command`, and list-shaped `args_prefix`.
- Referenced `provider` ids in routing / commands must exist.
- Unknown top-level keys remain forbidden by existing contract tests ([`CONFIG_TOP_LEVEL_KEYS`](../src/onward/config.py)); adding `providers` and `provider_registry` requires extending those frozensets and [architecture seam tests](../tests/test_architecture_seams.py).

---

## Non-goals (this design)

- Implementing adapters or shipping provider-specific CLIs.
- Changing default `ralph`-only behavior without `provider_registry.enabled: true`.
- Markdown / prose linting of provider docs.

---

## Summary

| Topic | Decision |
| ----- | -------- |
| Opt-in | `provider_registry.enabled`, default false |
| Config | `providers` + optional `models.routing` + optional command defaults |
| Resolution | Logical model from artifact/flags/config → alias expansion → routing → provider choice → spawn |
| Authority | When implemented, must match CLI behavior; until then, [LIFECYCLE.md](LIFECYCLE.md) and current executor path remain source of truth |
