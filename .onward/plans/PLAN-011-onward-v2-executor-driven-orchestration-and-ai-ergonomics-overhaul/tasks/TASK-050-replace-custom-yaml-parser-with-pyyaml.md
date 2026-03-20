---
id: "TASK-050"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-013"
project: ""
title: "Replace custom YAML parser with PyYAML"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:09Z"
updated_at: "2026-03-20T16:01:09Z"
---

# Context

CHUNK-013 is infrastructure cleanup. Onward uses a hand-rolled YAML parser (`_parse_simple_yaml` / `_dump_simple_yaml` in `util.py`) that handles basic key-value maps, lists, and nested structures. It's fragile: it doesn't handle multi-line strings, flow sequences with colons, quoted keys, or various edge cases that AI-generated frontmatter hits. Replacing it with PyYAML eliminates these bugs and reduces maintenance burden.

# Scope

- Add `pyyaml` to `pyproject.toml` dependencies
- Replace `_parse_simple_yaml` implementation with `yaml.safe_load`
- Replace `_dump_simple_yaml` implementation with `yaml.dump` (using `default_flow_style=False` for readability)
- Keep the public API stable: `parse_simple_yaml` and `dump_simple_yaml` remain the exported names
- Keep `split_frontmatter` unchanged (it's string splitting, not YAML parsing)
- Keep `_parse_scalar` for any edge-case handling that PyYAML doesn't cover (likely unnecessary — remove if not needed)
- Remove all the custom YAML parser helpers: `_read_dash_sequence`, `_mapping_yaml_list_item`, `_parse_simple_yaml`, `_dump_simple_yaml_lines`, `_format_scalar`
- Update `_dump_run_json_record` and `_read_run_json_record` — run records use JSON, not YAML; no change needed
- Run full test suite to catch regressions
- Verify all existing artifact files parse correctly with PyYAML

# Out of scope

- Changing the frontmatter format (still `---`-delimited YAML)
- Switching to TOML or any other format
- Adding YAML schema validation
- Changing the `index.yaml` or `recent.yaml` format

# Files to inspect

- `src/onward/util.py` — the entire YAML parser section (lines ~88-328), public names (lines ~416-429)
- `pyproject.toml` — dependencies
- `tests/` — all tests that exercise YAML parsing/dumping
- `.onward/plans/` — existing artifact files to verify parsing compatibility

# Implementation notes

- PyYAML `yaml.safe_load` handles everything the custom parser does, plus multi-line strings, anchors, and complex types. `safe_load` is appropriate (no arbitrary Python objects).
- PyYAML `yaml.dump` with `default_flow_style=False` produces block-style YAML similar to the custom dumper. Set `allow_unicode=True` for UTF-8 content.
- Key difference: PyYAML may quote strings differently (e.g., values that look like booleans or numbers). Test that frontmatter round-trips correctly: `parse_simple_yaml(dump_simple_yaml(metadata))` should equal `metadata`.
- The custom parser's `_parse_scalar` converts `"true"`/`"false"` to Python bools, numbers to int/float, `"null"` to None. PyYAML does the same by default with `safe_load`.
- The custom dumper uses `json.dumps()` for string quoting. PyYAML's default string quoting is different (single quotes, no quotes for simple strings). This changes the output format but not the semantics. Run all tests to verify.
- Watch for: timestamps like `"2026-03-20T16:01:02Z"` — PyYAML `safe_load` may parse these as `datetime` objects instead of strings. If so, use a custom loader or representer to keep them as strings. Alternatively, the frontmatter already quotes timestamps (`created_at: "2026-03-20T..."`) which prevents auto-conversion.
- The `_read_run_json_record` function has a fallback to `_parse_simple_yaml` for legacy YAML run records. After this change, it uses PyYAML — which is fine and handles more edge cases.

# Acceptance criteria

- `pyyaml` is in `pyproject.toml` dependencies
- `parse_simple_yaml` uses `yaml.safe_load` internally
- `dump_simple_yaml` uses `yaml.dump` internally
- Custom parser functions (`_read_dash_sequence`, `_mapping_yaml_list_item`, etc.) are removed
- All existing artifact files parse correctly (run `onward doctor`)
- Frontmatter round-trips: `parse(dump(metadata))` equals `metadata` for all existing artifacts
- All tests pass
- No new dependencies beyond `pyyaml`

# Handoff notes

- This is a high-confidence, low-risk change since PyYAML is a mature, well-tested library. The main risk is output format differences in `dump_simple_yaml` that break test assertions on exact string output.
- If tests compare exact YAML output strings, they may need updating for PyYAML's quoting style.
- The `_format_scalar` function uses `json.dumps` for string quoting — PyYAML uses YAML-native quoting. This is a cosmetic difference.
- After this lands, any YAML edge-case bugs are PyYAML's responsibility, not ours.
