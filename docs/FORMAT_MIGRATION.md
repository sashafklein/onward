# Persisted format migration notes

Onward keeps **read paths** tolerant of older workspace data while **new writes** use the current contract.

## Task run snapshots (`.onward/runs/RUN-*.json`)

- **Current write format:** strict JSON (UTF-8), one object per file, as produced by `onward work` and related paths.
- **Legacy read format:** files may contain **simple-YAML-shaped** text (subset parser, not full YAML). Readers try JSON first, then that legacy shape.
- **Sparse records:** snapshots from before optional fields were added may omit `plan`, `chunk`, `executor`, `error`, or `finished_at`. Readers merge defaults from `_RUN_RECORD_OPTIONAL_DEFAULTS` in `src/onward/util.py` (real values from the file always win) so CLI and index generation see a consistent key set. Stored files are not rewritten automatically.
- **`success_ack`:** optional object written when the executor prints a valid acknowledgment line and Onward parses it (including when `work.require_success_ack` is false but the line is present). Older snapshots omit this key.

**Future removal:** dropping YAML fallback or changing required run fields would be a **breaking major** change; workspaces would need a one-shot migration (re-save runs as JSON or regenerate from logs — policy TBD).

## Executor stdin JSON (Ralph / configured command)

- **Current contract:** every payload includes integer `schema_version` (currently **`1`**). Schema: [`schemas/onward-executor-stdin-v1.schema.json`](schemas/onward-executor-stdin-v1.schema.json).
- **Legacy:** stdin captured from older Onward builds may **omit** `schema_version` or set it to JSON `null`. For validation and custom executors, use `normalize_executor_stdin_payload()` in `onward.executor_payload` before interpreting fields, or rely on `validate_executor_stdin_payload()` which applies the same defaulting for missing/null version only (wrong non-null versions still fail).

**Outbound:** Onward always sets `schema_version` via `with_schema_version()` when invoking the executor.

## See also

- [Work handoff and runtime layout](WORK_HANDOFF.md)
- [Executor stdin schema README](schemas/README.md)
