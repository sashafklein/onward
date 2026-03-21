# Provider routing (superseded design)

**Status:** archived. The **provider registry** proposal on this page was never implemented. Onward now uses a **Python executor layer** instead: an `Executor` ABC, a **built-in** default that spawns Claude Code or Cursor agent CLIs from the resolved model string, and an optional **subprocess adapter** for the legacy stdin-JSON protocol.

**Use these instead:**

| Topic | Location |
| ----- | -------- |
| Executor interface (`TaskContext`, `ExecutorResult`, `execute_task` / `execute_batch`) | [`src/onward/executor.py`](../src/onward/executor.py) |
| Built-in CLI routing (`route_model_to_backend`, `BuiltinExecutor`, streaming) | [`src/onward/executor_builtin.py`](../src/onward/executor_builtin.py) |
| When built-in vs external command is chosen | [`resolve_executor` in `src/onward/config.py`](../src/onward/config.py) |
| Chunk/plan batch integration | [`src/onward/execution.py`](../src/onward/execution.py) |
| Reference shell wrapper (not the default path) | [`scripts/onward-exec`](../scripts/onward-exec) |

**Resolution today (summary):**

1. **Config:** `models` uses **tiered keys** (`default`, `high`, `medium`, `low`, `split`, `review_1`, `review_2`) with automatic fallback chains; see [CAPABILITIES.md](CAPABILITIES.md). Legacy flat keys (`task_default`, `split_default`, `review_default`) are still read but **`onward doctor` warns** — migrate to tiers.
2. **Tasks:** Explicit `model` in frontmatter wins; else `effort: high|medium|low` maps to a tier; else the `default` tier.
3. **Backend:** The built-in executor picks **Claude** vs **Cursor** from the model string (prefix/substring heuristics — e.g. `opus-*` → Claude, `cursor-*` / `gemini` → Cursor). An external `executor.command` (any value other than `builtin`) skips that and runs your command with the same JSON stdin as before.

No `provider_registry.enabled` flag or `providers:` table exists; extending routing means changing or subclassing executor code, not adding YAML from this old spec.

---

## Historical note (original design sketch)

The sections below described a **future** multi-provider registry. They are kept only as context for why the simpler executor-first approach was chosen. **Do not treat the YAML or resolution order below as current behavior.**

<details>
<summary>Original provider registry proposal (not implemented)</summary>

The old idea was an opt-in `provider_registry` block, named `providers`, optional `models.routing`, and command-level provider overrides. That would have required extending `CONFIG_TOP_LEVEL_KEYS` and new validation. The implemented design folds **routing into the built-in executor** (model string → CLI) and keeps **one external protocol** for custom executors.

</details>
