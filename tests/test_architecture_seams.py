"""Guardrails for package seams (config vs scaffold, CLI surface, imports, executor contract).

Extend these tests when you add config keys, new `onward.*` modules, or change executor stdin.
See docs/CONTRIBUTION.md → Architecture / seam tests.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import onward.executor_ack as executor_ack_mod
import onward.executor_payload as executor_payload_mod
from onward.config import (
    CONFIG_SECTION_KEYS,
    CONFIG_TOP_LEVEL_KEYS,
    config_raw_deprecation_warnings,
    config_validation_warnings,
    resolve_model_for_task,
    resolve_model_for_tier,
    validate_config_contract_issues,
)
from onward.scaffold import DEFAULT_FILES
from onward.util import parse_simple_yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
ONWARD_PKG = REPO_ROOT / "src" / "onward"
CLI_PY = ONWARD_PKG / "cli.py"
EXECUTOR_PY = ONWARD_PKG / "executor.py"
EXECUTOR_BUILTIN_PY = ONWARD_PKG / "executor_builtin.py"
EXECUTOR_SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "onward-executor-stdin-v1.schema.json"
SUCCESS_ACK_SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "onward-task-success-ack-v1.schema.json"
TASK_RESULT_V2_SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "onward-task-result-v2.schema.json"


def _iter_onward_importfrom_aliases(tree: ast.AST) -> list[tuple[int, str | None, str, str | None]]:
    """Yield (lineno, module, imported_name, as_name) for ImportFrom nodes targeting onward."""
    out: list[tuple[int, str | None, str, str | None]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        mod = node.module
        if mod != "onward" and not mod.startswith("onward."):
            continue
        for alias in node.names:
            out.append((node.lineno, mod, alias.name, alias.asname))
    return out


def test_resolve_model_for_tier_fallback_chains() -> None:
    assert resolve_model_for_tier({"models": {"default": "X"}}, "low") == "X"
    assert resolve_model_for_tier({"models": {"default": "X", "low": "Y"}}, "low") == "Y"
    assert resolve_model_for_tier({"models": {"default": "X", "medium": "Y"}}, "low") == "Y"


def test_resolve_model_for_tier_all_seven_keys_when_fully_configured() -> None:
    cfg = {
        "models": {
            "default": "D",
            "high": "H",
            "medium": "M",
            "low": "L",
            "split": "S",
            "review_1": "R1",
            "review_2": "R2",
        },
    }
    assert resolve_model_for_tier(cfg, "default") == "D"
    assert resolve_model_for_tier(cfg, "high") == "H"
    assert resolve_model_for_tier(cfg, "medium") == "M"
    assert resolve_model_for_tier(cfg, "low") == "L"
    assert resolve_model_for_tier(cfg, "split") == "S"
    assert resolve_model_for_tier(cfg, "review_1") == "R1"
    assert resolve_model_for_tier(cfg, "review_2") == "R2"


def test_resolve_model_for_tier_only_default_chains_all_tiers() -> None:
    cfg = {"models": {"default": "ONLY"}}
    for tier in ("high", "medium", "low", "split", "review_1", "review_2"):
        assert resolve_model_for_tier(cfg, tier) == "ONLY"


def test_resolve_model_for_tier_missing_models_uses_opus_latest() -> None:
    assert resolve_model_for_tier({}, "default") == "opus-latest"
    assert resolve_model_for_tier({}, "low") == "opus-latest"


def test_resolve_model_for_tier_models_not_dict() -> None:
    assert resolve_model_for_tier({"models": None}, "medium") == "opus-latest"  # type: ignore[dict-item]


def test_resolve_model_for_tier_all_intermediate_nulls_walk_to_default() -> None:
    cfg = {
        "models": {
            "default": "D",
            "high": None,  # type: ignore[dict-item]
            "medium": None,  # type: ignore[dict-item]
            "low": None,  # type: ignore[dict-item]
        },
    }
    assert resolve_model_for_tier(cfg, "low") == "D"


def test_resolve_model_for_tier_review_2_null_uses_high_then_default() -> None:
    cfg = {"models": {"default": "D", "high": "H"}}
    assert resolve_model_for_tier(cfg, "review_2") == "H"


def test_resolve_model_for_tier_review_1_prefers_high_over_default_when_high_set() -> None:
    cfg = {"models": {"default": "D", "high": "H", "review_1": None}}  # type: ignore[dict-item]
    assert resolve_model_for_tier(cfg, "review_1") == "H"


def test_resolve_model_for_tier_split_null_falls_to_default() -> None:
    cfg = {"models": {"default": "D", "split": None}}  # type: ignore[dict-item]
    assert resolve_model_for_tier(cfg, "split") == "D"


def test_resolve_model_for_tier_legacy_split_default_only() -> None:
    cfg = {"models": {"default": "D", "split_default": "sonnet-latest"}}
    assert resolve_model_for_tier(cfg, "split") == "sonnet-latest"


def test_resolve_model_for_tier_legacy_review_default_only() -> None:
    cfg = {"models": {"default": "D", "review_default": "opus-latest"}}
    assert resolve_model_for_tier(cfg, "review_1") == "opus-latest"


def test_resolve_model_for_tier_split_key_wins_over_split_default() -> None:
    cfg = {"models": {"default": "D", "split": "Y", "split_default": "X"}}
    assert resolve_model_for_tier(cfg, "split") == "Y"


def test_resolve_model_for_tier_review_1_wins_over_review_default() -> None:
    cfg = {"models": {"default": "D", "review_1": "Y", "review_default": "X"}}
    assert resolve_model_for_tier(cfg, "review_1") == "Y"


def test_config_raw_deprecation_warnings_legacy_model_keys() -> None:
    raw = {
        "models": {
            "default": "opus-latest",
            "task_default": "sonnet-latest",
            "split_default": "haiku-latest",
            "review_default": "opus-latest",
        },
    }
    msgs = config_raw_deprecation_warnings(raw)
    assert any("task_default" in m and "deprecated" in m for m in msgs)
    assert any("split_default" in m and "rename" in m for m in msgs)
    assert any("review_default" in m and "review_1" in m for m in msgs)


def test_config_raw_deprecation_warnings_both_split_and_split_default() -> None:
    raw = {"models": {"default": "D", "split": "Y", "split_default": "X"}}
    msgs = config_raw_deprecation_warnings(raw)
    assert any("ignored" in m and "split_default" in m for m in msgs)
    assert not any("rename to models.split" in m for m in msgs)


def test_config_raw_deprecation_warnings_both_review_1_and_review_default() -> None:
    raw = {"models": {"default": "D", "review_1": "Y", "review_default": "X"}}
    msgs = config_raw_deprecation_warnings(raw)
    assert any("ignored" in m and "review_default" in m for m in msgs)
    assert not any("rename to models.review_1" in m for m in msgs)


def test_validate_config_contract_accepts_legacy_model_keys() -> None:
    issues = validate_config_contract_issues(
        {
            "version": 1,
            "models": {
                "default": "opus-latest",
                "split_default": "sonnet-latest",
                "review_default": "opus-latest",
                "task_default": "haiku-latest",
            },
        },
    )
    assert issues == []


def test_resolve_model_for_task_explicit_model_wins() -> None:
    cfg = {"models": {"default": "opus-latest", "low": "haiku-latest"}}
    assert resolve_model_for_task(cfg, {"model": "custom-model"}) == "custom-model"
    assert resolve_model_for_task(cfg, {"model": "custom-model", "effort": "low"}) == "custom-model"


def test_resolve_model_for_task_effort_tiers() -> None:
    cfg = {
        "models": {
            "default": "D",
            "high": "H",
            "medium": "M",
            "low": "L",
        },
    }
    assert resolve_model_for_task(cfg, {"effort": "low"}) == "L"
    assert resolve_model_for_task(cfg, {"effort": "medium"}) == "M"
    assert resolve_model_for_task(cfg, {"effort": "high"}) == "H"
    assert resolve_model_for_task(cfg, {"effort": "LOW"}) == "L"


def test_resolve_model_for_task_empty_metadata_uses_default_tier() -> None:
    cfg = {"models": {"default": "D", "low": "L"}}
    assert resolve_model_for_task(cfg, {}) == "D"


def test_resolve_model_for_task_unknown_effort_falls_back_to_default_tier() -> None:
    cfg = {"models": {"default": "D", "low": "L"}}
    assert resolve_model_for_task(cfg, {"effort": "xl"}) == "D"
    assert resolve_model_for_task(cfg, {"effort": ""}) == "D"


def test_resolve_model_for_task_whitespace_only_model_ignored() -> None:
    """Blank or whitespace ``model`` is not explicit; resolution continues to effort / default."""
    cfg = {"models": {"default": "D", "low": "L"}}
    assert resolve_model_for_task(cfg, {"model": "   "}) == "D"
    assert resolve_model_for_task(cfg, {"model": "", "effort": "low"}) == "L"


def test_scaffold_default_config_yaml_matches_config_allowlists() -> None:
    raw = DEFAULT_FILES[".onward.config.yaml"]
    parsed = parse_simple_yaml(raw)
    assert isinstance(parsed, dict)

    issues = validate_config_contract_issues(parsed)
    assert issues == [], f"default scaffold config should pass doctor contract: {issues}"

    for key in parsed:
        assert key in CONFIG_TOP_LEVEL_KEYS, f"unexpected top-level key {key!r} in scaffold .onward.config.yaml"

    for section, allowed in CONFIG_SECTION_KEYS.items():
        block = parsed.get(section)
        if not isinstance(block, dict):
            continue
        for k in block:
            assert k in allowed, f"scaffold config section {section!r} has disallowed key {k!r}"


def test_validate_config_contract_flags_unknown_top_level_key() -> None:
    issues = validate_config_contract_issues({"version": 1, "not_a_real_key": True})
    assert issues, "expected unknown top-level key to be rejected"
    assert any("not_a_real_key" in msg for msg in issues)


def test_validate_config_contract_flags_unknown_nested_key() -> None:
    issues = validate_config_contract_issues({"version": 1, "sync": {"mode": "local", "made_up": 1}})
    assert issues, "expected unknown nested key to be rejected"
    assert any("made_up" in msg or "sync.made_up" in msg for msg in issues)


def test_validate_config_contract_flags_unknown_models_key() -> None:
    issues = validate_config_contract_issues({"version": 1, "models": {"default": "opus-latest", "made_up_tier": "x"}})
    assert issues, "expected unknown models.* key to be rejected"
    assert any("made_up_tier" in msg or "models.made_up_tier" in msg for msg in issues)


def test_validate_config_contract_rejects_non_string_model_values() -> None:
    issues = validate_config_contract_issues({"version": 1, "models": {"default": "opus-latest", "low": 99}})
    assert any("config.models.low" in msg and "string or null" in msg for msg in issues)


def test_validate_config_contract_rejects_empty_string_model_when_set() -> None:
    issues = validate_config_contract_issues({"version": 1, "models": {"default": "opus-latest", "low": "  "}})
    assert any("config.models.low" in msg and "non-empty string" in msg for msg in issues)


def test_config_validation_warnings_missing_models_default() -> None:
    msgs = config_validation_warnings({"models": {"low": "haiku-latest"}})
    assert any("models.default is unset" in m for m in msgs)


def test_config_validation_warnings_ambiguous_model_string() -> None:
    msgs = config_validation_warnings({"models": {"default": "opus-latest", "low": "weird-custom"}})
    assert any("config.models.low" in m and "routing hints" in m for m in msgs)


def test_config_validation_warnings_builtin_no_ai_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("onward.config.shutil.which", lambda _n: None)
    cfg = {"executor": {"enabled": True, "command": "builtin"}, "models": {"default": "opus-latest"}}
    msgs = config_validation_warnings(cfg)
    assert any("built-in executor" in m and "PATH" in m for m in msgs)


def test_config_validation_warnings_skips_cli_check_when_executor_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("onward.config.shutil.which", lambda _n: None)
    cfg = {"executor": {"enabled": False, "command": "builtin"}, "models": {"default": "opus-latest"}}
    msgs = config_validation_warnings(cfg)
    assert not any("built-in executor" in m and "PATH" in m for m in msgs)


def test_executor_module_avoids_heavy_integration_imports() -> None:
    tree = ast.parse(EXECUTOR_PY.read_text(encoding="utf-8"))
    mods = {mod for _, mod, _, _ in _iter_onward_importfrom_aliases(tree) if mod}
    assert "onward.execution" not in mods
    assert "onward.cli_commands" not in mods


def test_executor_builtin_avoids_cli_and_execution_imports() -> None:
    tree = ast.parse(EXECUTOR_BUILTIN_PY.read_text(encoding="utf-8"))
    mods = {mod for _, mod, _, _ in _iter_onward_importfrom_aliases(tree) if mod}
    assert "onward.cli_commands" not in mods
    assert "onward.execution" not in mods


def test_cli_entrypoint_only_imports_cli_commands_and_scaffold() -> None:
    tree = ast.parse(CLI_PY.read_text(encoding="utf-8"))
    onward_imports = _iter_onward_importfrom_aliases(tree)
    modules = {mod for _, mod, _, _ in onward_imports}
    assert modules == {"onward.cli_commands", "onward.scaffold"}, (
        "cli.py should stay a thin entrypoint: only onward.cli_commands and onward.scaffold; got " + str(sorted(modules))
    )

    by_mod: dict[str, list[str]] = {}
    for _, mod, name, _as in onward_imports:
        if name == "*":
            pytest.fail("cli.py must not use star-imports from onward")
        by_mod.setdefault(mod or "", []).append(name)

    assert by_mod["onward.scaffold"] == ["require_workspace"]
    for n in by_mod["onward.cli_commands"]:
        assert n.startswith("cmd_"), f"unexpected symbol from cli_commands: {n}"


def test_onward_executor_module_exports_protocol_and_executors() -> None:
    from onward.executor import BuiltinExecutor, Executor, ExecutorResult, SubprocessExecutor, TaskContext

    assert Executor.__name__ == "Executor"
    assert issubclass(BuiltinExecutor, Executor)
    assert issubclass(SubprocessExecutor, Executor)
    assert TaskContext.__dataclass_fields__["task"]  # type: ignore[attr-defined]
    assert ExecutorResult.__dataclass_fields__["success"]  # type: ignore[attr-defined]


def test_no_cross_module_private_onward_imports() -> None:
    """Fail if any `from onward.X import _foo` pulls a leading-underscore symbol (TASK-012 seam)."""
    bad: list[str] = []
    for path in sorted(ONWARD_PKG.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for lineno, mod, name, asname in _iter_onward_importfrom_aliases(tree):
            if name == "*":
                bad.append(f"{path.name}:{lineno}: star import from {mod}")
                continue
            if name.startswith("_"):
                bad.append(f"{path.name}:{lineno}: from {mod} import {name}" + (f" as {asname}" if asname else ""))
    assert not bad, "leading-underscore imports from onward.*:\n" + "\n".join(bad)


def test_task_success_ack_schema_version_matches_code() -> None:
    assert TASK_RESULT_V2_SCHEMA_PATH.is_file()
    schema = json.loads(TASK_RESULT_V2_SCHEMA_PATH.read_text(encoding="utf-8"))
    ver = schema["properties"]["onward_task_result"]["properties"]["schema_version"]["const"]
    assert ver == executor_ack_mod.SUCCESS_ACK_SCHEMA_VERSION


def test_executor_stdin_json_schema_is_valid_and_version_matches_code() -> None:
    assert EXECUTOR_SCHEMA_PATH.is_file(), f"missing schema at {EXECUTOR_SCHEMA_PATH}"
    schema = json.loads(EXECUTOR_SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema.get("$defs", {})
    for name, block in defs.items():
        props = block.get("properties") or {}
        sv = props.get("schema_version")
        if not isinstance(sv, dict) or "const" not in sv:
            continue
        assert sv["const"] == executor_payload_mod.EXECUTOR_PAYLOAD_SCHEMA_VERSION, (
            f"$defs.{name} schema_version const must match EXECUTOR_PAYLOAD_SCHEMA_VERSION "
            f"({executor_payload_mod.EXECUTOR_PAYLOAD_SCHEMA_VERSION})"
        )


def test_executor_payload_required_sets_match_json_schema() -> None:
    schema = json.loads(EXECUTOR_SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema["$defs"]

    assert set(defs["task"]["required"]) == executor_payload_mod._TASK_REQUIRED
    assert set(defs["review"]["required"]) == executor_payload_mod._REVIEW_REQUIRED

    hook_task = set(defs["hookTaskMarkdown"]["required"])
    assert hook_task == executor_payload_mod._HOOK_COMMON | executor_payload_mod._HOOK_TASK_EXTRA

    hook_chunk = set(defs["hookChunkMarkdown"]["required"])
    assert hook_chunk == executor_payload_mod._HOOK_COMMON | executor_payload_mod._HOOK_CHUNK_EXTRA
