---
id: "CHUNK-018"
type: "chunk"
plan: "PLAN-012"
project: ""
title: "Docs, config validation, and cleanup"
status: "completed"
description: "Update documentation, config validation, architecture tests, and add comprehensive test coverage for the new executor architecture."
priority: "medium"
model: "composer-2"
depends_on:
- "CHUNK-017"
created_at: "2026-03-20T21:50:09Z"
updated_at: "2026-03-21T00:17:40Z"
---

# Summary

Final cleanup: update all documentation to reflect the new executor architecture and tiered model config. Extend `onward doctor` to validate the new config shape. Add architecture seam tests for new modules. Ensure comprehensive test coverage across all new code.

# Scope

- Update `docs/PROVIDER_REGISTRY.md` to point at new executor architecture (or archive)
- Update `docs/CAPABILITIES.md` for built-in executor and batch semantics
- Update `docs/LIFECYCLE.md` for batch chunk/plan execution details
- Extend config validation for new model keys and executor resolution
- Architecture seam tests for `executor.py` and `executor_builtin.py`
- Comprehensive test suite: model fallback chains, CLI routing, batch execution, external adapter

# Out of scope

- Functional changes to executor or config (all in earlier chunks)

# Dependencies

- CHUNK-017 (batch execution) -- all functional work must be complete

# Expected files/systems involved

- `docs/PROVIDER_REGISTRY.md`, `docs/CAPABILITIES.md`, `docs/LIFECYCLE.md`
- `src/onward/config.py` -- validation extensions
- `tests/test_architecture_seams.py` -- seam tests for new modules
- `tests/test_executor.py` -- new: protocol and adapter tests
- `tests/test_executor_builtin.py` -- new: routing, prompt building, streaming tests

# Completion criteria

- [ ] `onward doctor` validates new model config keys and reports issues
- [ ] `PROVIDER_REGISTRY.md` reflects the executor protocol (or is archived with pointer)
- [ ] `CAPABILITIES.md` documents built-in executor and batch execution
- [ ] Architecture seam tests verify `executor.py` and `executor_builtin.py` module boundaries
- [ ] Test coverage for: model fallback chains, CLI routing patterns, batch iterator, SubprocessExecutor equivalence
