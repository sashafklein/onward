# Schemas

- **`onward-executor-stdin-v1.schema.json`** — JSON Schema (draft 2020-12) for JSON passed on the executor’s stdin (`onward work`, markdown hooks, `onward review-plan`). Version **`1`** matches the `schema_version` field in each payload.

- **`onward-task-success-ack-v1.schema.json`** — optional JSON line the executor prints when `work.require_success_ack` is true; stored on the run record as `success_ack`.

Legacy captured stdin may omit `schema_version`; see [Format migration](../FORMAT_MIGRATION.md).
