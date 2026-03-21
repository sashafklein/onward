import json

from onward.executor_payload import (
    EXECUTOR_PAYLOAD_SCHEMA_VERSION,
    normalize_executor_stdin_payload,
    validate_executor_stdin_payload,
    with_schema_version,
)


def test_with_schema_version_sets_version():
    p = with_schema_version({"type": "task", "run_id": "x"})
    assert p["schema_version"] == EXECUTOR_PAYLOAD_SCHEMA_VERSION
    assert p["type"] == "task"


def test_validate_task_payload_ok():
    p = with_schema_version(
        {
            "type": "task",
            "run_id": "RUN-1",
            "task": {"id": "TASK-001"},
            "body": "x",
            "notes": None,
            "notes_hint": "hint",
            "chunk": None,
            "plan": None,
        }
    )
    assert validate_executor_stdin_payload(p) == []


def test_validate_review_payload_ok():
    p = with_schema_version(
        {
            "type": "review",
            "model": "m",
            "plan_id": "PLAN-001",
            "prompt": "p",
            "plan_metadata": {},
            "plan_body": "b",
        }
    )
    assert validate_executor_stdin_payload(p) == []


def test_validate_hook_task_payload_ok():
    p = with_schema_version(
        {
            "type": "hook",
            "phase": "post_task_markdown",
            "run_id": "RUN-1",
            "model": "m",
            "hook_path": "h.md",
            "hook_body": "x",
            "task": {},
            "task_body": "t",
        }
    )
    assert validate_executor_stdin_payload(p) == []


def test_validate_hook_chunk_payload_ok():
    p = with_schema_version(
        {
            "type": "hook",
            "phase": "post_chunk_markdown",
            "model": "m",
            "hook_path": "h.md",
            "hook_body": "x",
            "chunk": {},
            "chunk_body": "c",
        }
    )
    assert validate_executor_stdin_payload(p) == []


def test_validate_split_payload_ok():
    p = with_schema_version(
        {
            "type": "split",
            "model": "opus",
            "prompt": "instructions",
            "artifact_metadata": {"id": "PLAN-001", "type": "plan"},
            "artifact_body": "# Plan\n",
            "split_type": "plan",
        }
    )
    assert validate_executor_stdin_payload(p) == []


def test_validate_rejects_wrong_version():
    p = {"type": "task", "schema_version": 99}
    issues = validate_executor_stdin_payload(p)
    assert any("schema_version" in i for i in issues)


def test_validate_accepts_legacy_missing_schema_version():
    p = {
        "type": "task",
        "run_id": "RUN-1",
        "task": {"id": "TASK-001"},
        "body": "x",
        "notes": None,
        "notes_hint": "hint",
        "chunk": None,
        "plan": None,
    }
    assert validate_executor_stdin_payload(p) == []


def test_validate_accepts_legacy_null_schema_version():
    p = {
        "type": "task",
        "schema_version": None,
        "run_id": "RUN-1",
        "task": {"id": "TASK-001"},
        "body": "x",
        "notes": None,
        "notes_hint": "hint",
        "chunk": None,
        "plan": None,
    }
    assert validate_executor_stdin_payload(p) == []


def test_normalize_executor_stdin_payload_fills_missing_version():
    p = {"type": "task", "run_id": "x"}
    n = normalize_executor_stdin_payload(p)
    assert n["schema_version"] == EXECUTOR_PAYLOAD_SCHEMA_VERSION
    assert "schema_version" not in p


def test_schema_file_is_valid_json():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "docs" / "schemas" / "onward-executor-stdin-v1.schema.json"
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data["$defs"]["task"]["properties"]["type"]["const"] == "task"
    assert data["$defs"]["task"]["required"]
    assert data["$defs"]["split"]["properties"]["type"]["const"] == "split"
