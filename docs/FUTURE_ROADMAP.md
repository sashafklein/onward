<!--
Last updated: 2026-03-20
-->

# Future roadmap (parking lot)

This file is **not a commitment** — it collects deferred ideas and vision items so they are not lost. Promote entries to real Onward plans in `.onward/plans/` when you intend to build them.

---

## Execution & orchestration

**Parallel task execution within chunks** — Run multiple ready tasks concurrently with isolated worktrees; complexity **high**; needs clear run-record and status semantics.

**Parallel chunk / worktree-per-chunk** — Broader parallelism at chunk level; **high**; depends on stable task-level story.

**Daemon / orchestrator mode** — Long-running process that watches artifacts and dispatches work; **high**; prerequisite: reliable idempotency and locking.

**Exponential backoff for retries** — Complement `work.max_retries` with backoff between failures (from circuit-breaker work); **low–medium**.

**Per-task overrides in frontmatter** — `max_retries`, `timeout`, `executor` per task; **medium**; schema + lifecycle updates.

**Plan-level hooks** — `pre_plan_shell`, `post_plan_markdown` for plan-wide orchestration; **medium** (see hook cleanup CHUNK-013).

---

## Index & data plane

**Incremental index (`index.yaml`)** — Patch index on writes instead of full regeneration; **medium**; prerequisite: invariant tests for index shape.

**`onward migrate`** — Schema upgrades and `blocked_by` → `depends_on` rewriting; **medium** (deferred from TASK-037).

**`--auto-fix` for split validation** — Optional repair of AI split output (TASK-040); **medium**.

---

## Multi-project & workspace

**Cross-workspace dependencies** — Artifacts that depend on another repo’s Onward workspace; **high**; needs discovery and sync story.

**Multi-value project filtering** — Richer `--project` filters (TASK-048); **low**.

**Effort-based `onward next` sorting** — Order by `effort` metadata (TASK-047); **low**.

---

## UX & observability

**Web dashboard** — Read-only UI for plans, progress, run history; **high**; optional separate process reading repo state.

**Metrics & reporting** — Durations, success rates, cost estimates; **medium**; needs opt-in telemetry from run records.

---

## Ecosystem

**Executor plugins / marketplace** — Pluggable executors and shared scripts; **high**; builds on stdin JSON contract.

**Template system** — User-defined artifact templates beyond defaults; **low–medium**.

**Plugin system** — Loadable Python extensions for commands/hooks; **high**; security and packaging model required.

---

## Items surfaced during PLAN-011

**Model routing in executor** — Onward passes model strings through; richer routing stays in executor / future provider registry.

**Structured task result follow-ups** — Already in progress; extend with more validation as needed.

**Recovery docs** — [`RECOVERY.md`](RECOVERY.md) is canonical; link from reports optionally later.
