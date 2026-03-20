# Schemas

- **`onward-executor-stdin-v1.schema.json`** — JSON Schema (draft 2020-12) for JSON passed on the executor’s stdin (`onward work`, markdown hooks, `onward review-plan`). Version **`1`** matches the `schema_version` field in each payload.

Legacy captured stdin may omit `schema_version`; see [Format migration](../FORMAT_MIGRATION.md).
