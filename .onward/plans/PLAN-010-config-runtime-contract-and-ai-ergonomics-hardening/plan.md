---
id: "PLAN-010"
type: "plan"
project: ""
title: "Config-runtime contract and AI ergonomics hardening"
status: "open"
description: ""
priority: "medium"
model: "opus-latest"
created_at: "2026-03-20T00:22:07Z"
updated_at: "2026-03-20T00:22:07Z"
---

# Summary

Harden Onward so its documentation, configuration surface, and runtime behavior match exactly. Eliminate surprising behavior that causes humans and AI agents to form incorrect mental models. Produce a system where an agent that follows installation instructions can reliably operate without hidden assumptions.

# Problem

The current system has contract drift: documented capabilities and config keys that are partially implemented, unused, or hardcoded away. This creates a trust gap where "what docs say" and "what code does" diverge.

For an AI-first orchestration tool, contract drift is multiplicative risk:
- agents overfit to docs and fail in runtime,
- humans overfit to runtime quirks and create folklore,
- future contributors cannot tell which layer is authoritative.

The repo needs strict alignment between:
- public docs,
- config schema,
- CLI behavior,
- persisted artifact formats,
- executor payload contracts.

Recent dogfood stress testing added concrete failures:
- Dogfood runtime packaging can be misaligned (entrypoint portability and Python version parity).
- `review-plan` lacks a clear multi-provider model key/routing strategy.
- `work` can mark tasks complete even when executor did not actually execute the requested task semantics.
- Chunk completion and `next` selection can surface non-actionable work.
- Some CLI output and labeling create avoidable ambiguity.

# Goals

- Make config and docs truthful: every declared knob is either enforced or removed.
- Make persisted formats and schemas machine-safe and explicit.
- Make lifecycle semantics unambiguous across command behavior and docs.
- Strengthen module boundaries so extensions do not require editing `cli.py`.
- Validate the full AI onboarding path with end-to-end realism.
- Add provider-interop support so model execution can span OpenClaw and Cursor/Claude command-line surfaces with explicit routing/credentials.
- Ensure task success semantics require proof of meaningful execution, not only process exit status.

# Non-goals

- Rebuild the product vision or artifact model (Plan -> Chunk -> Task remains).
- Replace the current executor abstraction with a new subsystem.
- Add speculative features not tied to trust/contract hardening.
- Optimize performance beyond what is required for correctness and ergonomics.

# End state

- [ ] As an agent, when I read docs and config, runtime behavior matches without surprises.
- [ ] As a maintainer, I can change behavior by updating a clear service module and tests, not by patching `cli.py` glue everywhere.
- [ ] As an integrator, I can parse run files and payloads using stable, versioned contracts.
- [ ] As a contributor, I can detect drift via doctor/lint/test checks before merging.
- [ ] As a user, I can bootstrap and run the agent loop from installation docs without hidden tribal knowledge.

# Context

Observed high-risk mismatches (from architecture review):
- Config keys in templates/docs are not fully wired at runtime (`path`, `work.*`, `ralph.enabled`).
- `.json` run files currently hold YAML-like data.
- "AI-assisted split/review" framing overstates actual default split behavior (heuristic fallback).
- Lifecycle guidance in docs is stricter than enforced transitions.
- CLI still centralizes substantial policy logic and relies on private cross-module calls.

# Proposed approach

Phase 1: Kill contract drift first (highest risk reduction)

1) Build explicit contract inventory
- Enumerate all user-facing contract surfaces:
  - `.onward.config.yaml` template/defaults
  - README, INSTALLATION, CONTRIBUTION docs
  - CLI flags/help text
  - persisted files under `.onward/`
  - executor payload structures
- Produce a single "declared vs actual" matrix.

2) Resolve config contradictions decisively
- For each config key, pick one:
  - implement and test, or
  - deprecate/remove and document migration.
- No zombie keys.
- Add `doctor` checks for:
  - unsupported keys,
  - contradictory settings,
  - keys known to be ignored.

3) Normalize persisted format truth
- Ensure `.json` files contain JSON and are parsed as JSON.
- If compatibility required:
  - add tolerant read path,
  - add explicit migration behavior,
  - mark legacy behavior in docs and changelog.

Phase 2: Make behavior predictable for humans and AIs

4) Choose a lifecycle policy and enforce it everywhere
- Decide one model:
  - strict manual transitions (`start` then `work` then `complete`), or
  - work-owned transitions (commands auto-manage status).
- Update command behavior, error messages, and docs to one coherent model.
- Add tests for invalid transitions and expected happy paths.

5) Clarify AI claims and execution semantics
- Keep docs precise:
  - what is model-backed,
  - what is heuristic fallback,
  - what is env-override/test-only.
- Add a short "capability truth table" in docs.
- Address specific UX and semantics bugs:
  - chunk completion when all child tasks are completed,
  - `next` should not return non-actionable chunks,
  - clarify/fix open tree semantics (naming vs filtering),
  - document `(A)` and `(H)` markers in CLI help/docs,
  - correct split dry-run labels by artifact type.

Phase 2.5: Provider interoperability + model access strategy (OpenClaw target)

5b) Introduce explicit provider routing
- Design config to map model families/aliases to providers (example targets: OpenClaw backend, Claude CLI, Cursor agent CLI).
- Allow per-command routing policy (`split`, `review-plan`, `work`, hooks) and per-reviewer matrix selection.
- Add deterministic fallback behavior with transparent logs when a provider/model is unavailable.

5c) Add credentials and toolchain preflight
- Validate availability of required CLIs and credentials before expensive operations.
- Return actionable failures (missing key, missing binary, unsupported model/provider pair).
- Add clear "degraded mode" behavior where appropriate.

5d) Enforce execution success contract
- Define what counts as a successful `work` run (for example: explicit task acknowledgment/result schema from executor).
- Reject false positives like "exit 0 with no task handling".
- Record structured evidence of completion in run artifacts.

Phase 3: Strengthen maintainability seams

6) Extract orchestration policy out of CLI entrypoint
- Keep `cli.py` as parser/dispatch.
- Move domain policies into service modules with stable function signatures.
- Replace private underscore imports across modules with explicit public APIs.

7) Add architecture guardrails in tests
- Contract tests:
  - config key usage parity,
  - doc command existence sanity,
  - persisted format consistency,
  - payload schema validation.
- Regression tests to block reintroduction of drift.

Phase 4: Prove onboarding works in reality

8) End-to-end AI onboarding simulation
- Fresh workspace from install instructions only.
- Agent instruction block applied exactly as documented.
- Run full loop:
  - `report -> new plan/chunk/task -> start -> work -> complete -> report`.
- Verify expected artifacts, statuses, and outputs without manual hidden steps.
- Include dogfood packaging parity checks:
  - supported Python version in venv,
  - entrypoint portability on target shell PATH behavior,
  - deterministic requirement for `init`/workspace bootstrap in fixture flows.

9) Add CI-visible drift checks
- Add lightweight checks that fail PRs on:
  - stale docs command surfaces,
  - stale config templates,
  - contract/schema mismatches.

Execution order and dependencies
- CHUNK-002 (config contract) before CHUNK-004/005/006.
- CHUNK-003 (formats/schemas) before broader onboarding validation.
- CHUNK-004 (lifecycle semantics) before doc finalization.
- CHUNK-005 can partially run in parallel after CHUNK-002 decisions are made.
- CHUNK-006 runs last as proof and feedback loop.

Risk handling
- Backward compatibility risk:
  - provide migration notes and permissive readers where needed.
- Scope creep risk:
  - enforce "no new net features" rule in this plan.
- Behavioral break risk:
  - add golden-path end-to-end tests before refactors land.
- Integration risk with multi-provider execution:
  - stage rollout behind explicit config flags and maintain single-provider default path.

# Key artifacts

- `src/onward/cli.py`
- `src/onward/config.py`
- `src/onward/artifacts.py`
- `src/onward/execution.py`
- `src/onward/split.py`
- `src/onward/sync.py`
- `src/onward/scaffold.py`
- `scripts/dogfood/bootstrap.sh`
- `scripts/dogfood/e2e.sh`
- `.dogfood/consumer-app/.onward.config.yaml`
- `tests/test_cli_*.py`
- `tests/test_sync.py`
- `README.md`
- `INSTALLATION.md`
- `docs/CONTRIBUTION.md`
- `docs/WORK_HANDOFF.md`
- `.onward/templates/*`
- `.onward/prompts/*`

# Acceptance criteria

- Config contract parity
  - Every key in template/docs has runtime handling and tests, or is removed/deprecated with migration notes.
  - `doctor` reports unsupported/ignored keys and exits non-zero when detected.
- Format/schema integrity
  - `.json` runtime files are valid JSON.
  - Executor payloads for task/review/hook have documented required fields and schema checks in tests.
- Lifecycle coherence
  - CLI transition behavior matches one documented policy with explicit tests for valid/invalid flows.
  - README/INSTALLATION/CONTRIBUTION show the same lifecycle rules and command expectations.
- Boundary quality
  - `cli.py` no longer carries avoidable policy logic that belongs in services.
  - Cross-module calls use stable interfaces instead of private internals where practical.
- AI onboarding proof
  - Fresh install + configured agent instructions produce successful end-to-end loop with no undocumented recovery steps.
  - Drift checks exist and fail on intentional doc/config mismatch.
- Provider interoperability
  - `review-plan` supports explicit reviewer provider/model matrix (at least OpenClaw-targeted path with Claude + Cursor agent CLI options documented/tested).
  - Preflight catches missing provider credentials/tooling before running reviewers.
- Execution truthfulness
  - `onward work` cannot mark completion on generic executor success without task-level success proof.
- Dogfood reliability
  - Dogfood workflow uses supported Python runtime and working CLI entrypoint behavior.
  - Fresh dogfood run does not require undocumented manual `init` reconciliation.
- UX correctness
  - `next`, chunk completion, tree labeling/filtering, and split dry-run labels match documented intent and pass regression tests.

# Notes

Success standard for this plan: an AI agent should be able to operate correctly by following docs and command feedback alone, without human folklore or source-diving.
