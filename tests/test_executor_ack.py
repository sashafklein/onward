"""Unit tests for task success acknowledgment parsing."""

from __future__ import annotations

import json

from onward.executor_ack import SUCCESS_ACK_SCHEMA_VERSION, find_task_success_ack, parse_task_result


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


def test_find_ack_v1_backward_compat() -> None:
    line = json.dumps(
        {"onward_task_result": {"status": "completed", "schema_version": 1, "run_id": "RUN-abc"}}
    )
    found, err, obj = find_task_success_ack(line, "", "RUN-abc")
    assert found and not err
    assert obj is not None
    pr = parse_task_result(obj)
    assert pr["schema_version"] == 1
    assert pr["files_changed"] == []


def test_find_ack_v2_extended() -> None:
    payload = {
        "onward_task_result": {
            "schema_version": 2,
            "status": "completed",
            "run_id": "RUN-z",
            "summary": "Shipped",
            "files_changed": ["a.py", "b.py"],
            "follow_ups": [
                {"title": "T", "description": "D", "priority": "low"},
                {"title": "Bad", "description": ""},
            ],
            "acceptance_met": ["c1"],
            "acceptance_unmet": [],
            "notes": "n",
        }
    }
    line = json.dumps(payload)
    found, err, obj = find_task_success_ack(line, "", "RUN-z")
    assert found and not err
    pr = parse_task_result(obj)
    assert pr["schema_version"] == 2
    assert pr["summary"] == "Shipped"
    assert pr["files_changed"] == ["a.py", "b.py"]
    assert len(pr["follow_ups"]) == 1
    assert pr["follow_ups"][0]["title"] == "T"
    assert pr["acceptance_met"] == ["c1"]
    assert pr["notes"] == "n"


def test_find_ack_v2_invalid_files_changed_type_fails() -> None:
    line = json.dumps(
        {
            "onward_task_result": {
                "schema_version": 2,
                "status": "completed",
                "files_changed": "not-a-list",
            }
        }
    )
    found, err, obj = find_task_success_ack(line, "", "RUN-x")
    assert not found
    assert "files_changed" in err
    assert obj is None


def test_parse_task_result_defaults() -> None:
    pr = parse_task_result(
        {"onward_task_result": {"status": "completed", "schema_version": 1}}
    )
    assert pr["summary"] == ""
    assert pr["files_changed"] == []
    assert pr["follow_ups"] == []
    assert pr["acceptance_met"] == []
    assert pr["acceptance_unmet"] == []
    assert pr["notes"] == ""


def test_parse_task_result_invalid_wrapper() -> None:
    pr = parse_task_result({})
    assert pr["files_changed"] == []


def test_parse_task_result_skips_invalid_follow_up_objects() -> None:
    obj = {
        "onward_task_result": {
            "schema_version": 2,
            "status": "completed",
            "follow_ups": [
                {"title": "ok", "description": "yes"},
                "not-a-dict",
                {"title": "", "description": "x"},
            ],
        }
    }
    pr = parse_task_result(obj)
    assert len(pr["follow_ups"]) == 1
