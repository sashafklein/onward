---
id: "PLAN-005"
type: "plan"
title: "Sync modes, reliability hardening, and release readiness"
status: "completed"
description: "Add shared planning sync and tighten correctness for daily use"
priority: "medium"
model: "gpt-5"
created_at: "2026-03-19T00:00:00Z"
updated_at: "2026-03-20T00:02:33Z"
---

# Summary

Add local/shared sync support and harden Onward for stable repeated use.

# Problem

Without sync and hardening, Onward is constrained to one local environment and is fragile under real execution pressure.

# Goals

- Implement `onward sync push`, `sync pull`, `sync status`.
- Support same-repo branch sync and separate repo sync mode.
- Improve diagnostics, error handling, and migration checks.

# Non-goals

- Full multi-user locking.
- Complex conflict resolution workflows.

# Context

Sync is best-effort and file-based; artifacts remain canonical.

# Proposed approach

Add a sync implementation driven by `.onward.config.yaml` that mirrors `.onward/plans/` (including derived indexes) to the configured sync checkout.

# Risks

- Divergent state if sync pull/push semantics are unclear.
- Poor conflict messaging causing user confusion.

# Chunking strategy

1. Config + mode resolution.
2. Push/pull/status command plumbing.
3. Reliability pass: tests, doctor checks, and migration tools.

# Acceptance criteria

- `onward sync status` reports dirty/clean state for local and configured target (or uninitialized remote checkout).
- `onward sync push` publishes `.onward/plans/` to the selected sync target.
- `onward sync pull` integrates remote plan changes into the local workspace.
- Doctor includes sync config validation and clear remediation guidance.
- End-to-end smoke tests pass for local mode and one shared mode.

# Notes

Deliver this plan after `PLAN-004` so runtime semantics are stable first.
