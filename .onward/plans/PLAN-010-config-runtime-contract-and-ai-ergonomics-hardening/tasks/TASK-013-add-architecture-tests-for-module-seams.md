---
id: "TASK-013"
type: "task"
plan: "PLAN-010"
chunk: "CHUNK-005"
project: ""
title: "Add architecture tests for module seams"
status: "completed"
description: "Prevent boundary regressions with focused unit tests"
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T00:22:22Z"
updated_at: "2026-03-20T01:13:24Z"
---

# Context

PLAN-010 phase 3 §7 + acceptance: **contract / architecture guardrails** — block reintroduction of config drift, forbidden imports, stale commands in docs, etc.

# Scope

- Add tests: e.g. scaffold template keys vs `CONFIG_*` allowlists; `cli.py` import rules; optional AST grep for private imports.
- Persisted format smoke checks where not already covered.
- Payload/schema validation hooks if missing.

# Out of scope

- Full static type enforcement of entire codebase; runtime performance tests.

# Files to inspect

- `tests/`, `src/onward/config.py`, `src/onward/scaffold.py`, `docs/schemas/`, TASK-004 handoff suggestions

# Implementation notes

- Keep tests fast and deterministic; run in default `pytest` CI.

# Acceptance criteria

- New tests fail on intentional drift fixtures; documented in CONTRIBUTION how to extend checks.

# Handoff notes

- Added `tests/test_architecture_seams.py`: scaffold default config vs `CONFIG_*` allowlists + `validate_config_contract_issues`, negative contract cases, `cli.py` import surface, AST guard against `from onward… import _…`, executor JSON schema file validity + `schema_version` const vs code + required-key parity with `executor_payload` frozensets.
- Documented how to extend checks in `docs/CONTRIBUTION.md` (Architecture / seam tests).
- Full `pytest tests/` passes.
