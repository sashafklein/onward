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
    validate_config_contract_issues,
)
from onward.scaffold import DEFAULT_FILES
from onward.util import parse_simple_yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
ONWARD_PKG = REPO_ROOT / "src" / "onward"
CLI_PY = ONWARD_PKG / "cli.py"
EXECUTOR_SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "onward-executor-stdin-v1.schema.json"
SUCCESS_ACK_SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "onward-task-success-ack-v1.schema.json"


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
    assert SUCCESS_ACK_SCHEMA_PATH.is_file()
    schema = json.loads(SUCCESS_ACK_SCHEMA_PATH.read_text(encoding="utf-8"))
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
