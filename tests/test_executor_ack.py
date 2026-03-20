"""Unit tests for task success acknowledgment parsing."""

from __future__ import annotations

import json

import pytest

from onward.executor_ack import SUCCESS_ACK_SCHEMA_VERSION, find_task_success_ack


def test_find_ack_minimal_line() -> None:
    line = json.dumps(
        {"onward_task_result": {"status": "completed", "schema_version": SUCCESS_ACK_SCHEMA_VERSION}}
    )
    found, err, obj = find_task_success_ack(f"noise\n{line}\n", "", "RUN-x-TASK-001")
    assert found and not err
    assert obj is not None
    assert obj["onward_task_result"]["status"] == "completed"


def test_find_ack_prefers_last_matching_line() -> None:
    good = json.dumps(
        {"onward_task_result": {"status": "completed", "schema_version": SUCCESS_ACK_SCHEMA_VERSION}}
    )
    text = f"{good}\n{good}\n"
    found, err, obj = find_task_success_ack(text, "", "RUN-x")
    assert found and obj is not None


def test_find_ack_on_stderr() -> None:
    line = json.dumps(
        {"onward_task_result": {"status": "completed", "schema_version": SUCCESS_ACK_SCHEMA_VERSION}}
    )
    found, err, obj = find_task_success_ack("", f"log\n{line}", "RUN-x")
    assert found and obj is not None


def test_find_ack_run_id_mismatch_fails() -> None:
    line = json.dumps(
        {
            "onward_task_result": {
                "status": "completed",
                "schema_version": SUCCESS_ACK_SCHEMA_VERSION,
                "run_id": "WRONG",
            }
        }
    )
    found, err, obj = find_task_success_ack(line, "", "RUN-expected")
    assert not found
    assert "run_id mismatch" in err
    assert obj is None


def test_find_ack_wrong_status_fails() -> None:
    line = json.dumps(
        {"onward_task_result": {"status": "failed", "schema_version": SUCCESS_ACK_SCHEMA_VERSION}}
    )
    found, err, obj = find_task_success_ack(line, "", "RUN-x")
    assert not found
    assert obj is None


def test_find_ack_missing() -> None:
    found, err, obj = find_task_success_ack("hello\nworld\n", "", "RUN-x")
    assert not found
    assert "missing onward_task_result" in err
    assert obj is None
