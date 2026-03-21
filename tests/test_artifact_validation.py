"""Unit tests for validate_artifact() in onward.artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from onward.artifacts import Artifact, validate_artifact

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TASK_PATH = Path("fake/TASK-001.md")
_CHUNK_PATH = Path("fake/CHUNK-001.md")
_PLAN_PATH = Path("fake/PLAN-001.md")

_BASE_TASK = {
    "id": "TASK-001",
    "type": "task",
    "plan": "PLAN-001",
    "chunk": "CHUNK-001",
    "title": "Do a thing",
    "status": "open",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

_BASE_CHUNK = {
    "id": "CHUNK-001",
    "type": "chunk",
    "plan": "PLAN-001",
    "title": "Build stuff",
    "status": "open",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

_BASE_PLAN = {
    "id": "PLAN-001",
    "type": "plan",
    "title": "Alpha",
    "status": "open",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def _task(**overrides) -> Artifact:
    return Artifact(file_path=_TASK_PATH, body="", metadata={**_BASE_TASK, **overrides})


def _chunk(**overrides) -> Artifact:
    return Artifact(file_path=_CHUNK_PATH, body="", metadata={**_BASE_CHUNK, **overrides})


def _plan(**overrides) -> Artifact:
    return Artifact(file_path=_PLAN_PATH, body="", metadata={**_BASE_PLAN, **overrides})


# ---------------------------------------------------------------------------
# Valid artifacts → no issues
# ---------------------------------------------------------------------------


def test_valid_task_no_issues():
    assert validate_artifact(_task()) == []


def test_valid_chunk_no_issues():
    assert validate_artifact(_chunk()) == []


def test_valid_plan_no_issues():
    assert validate_artifact(_plan()) == []


# ---------------------------------------------------------------------------
# Field-level validation failures
# ---------------------------------------------------------------------------


def test_bad_status():
    issues = validate_artifact(_task(status="garbage"))
    assert any("status" in i for i in issues), issues


def test_bad_priority():
    issues = validate_artifact(_task(priority="urgent"))
    assert any("priority" in i for i in issues), issues


def test_bad_effort():
    issues = validate_artifact(_task(effort="huge"))
    assert any("effort" in i for i in issues), issues


def test_bad_complexity():
    issues = validate_artifact(_task(complexity="banana"))
    assert any("complexity" in i for i in issues), issues


def test_bad_model():
    issues = validate_artifact(_task(model="nonexistent-model-xyz"))
    assert any("model" in i for i in issues), issues


def test_bad_human_string():
    issues = validate_artifact(_task(human="maybe"))
    assert any("human" in i for i in issues), issues


# ---------------------------------------------------------------------------
# Unknown frontmatter field
# ---------------------------------------------------------------------------


def test_unknown_field():
    issues = validate_artifact(_task(foobar=1))
    assert any("unknown task field" in i and "foobar" in i for i in issues), issues


# ---------------------------------------------------------------------------
# Valid optional fields → no issues
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"effort": "m"},
        {"effort": "xl"},
        {"complexity": "low"},
        {"complexity": "high"},
        {"model": "sonnet"},
        {"model": "claude-sonnet-4-6"},
        {"human": True},
        {"human": False},
        {"priority": "high"},
        {"priority": "low"},
        {"effort": "m", "model": "sonnet", "human": True, "priority": "high"},
    ],
)
def test_valid_optional_fields_no_issues(kwargs):
    assert validate_artifact(_task(**kwargs)) == [], kwargs


# ---------------------------------------------------------------------------
# Unknown artifact type
# ---------------------------------------------------------------------------


def test_unknown_type():
    artifact = Artifact(
        file_path=Path("fake/UNKNOWN-001.md"),
        body="",
        metadata={"id": "UNKNOWN-001", "type": "widget"},
    )
    issues = validate_artifact(artifact)
    assert any("unknown type" in i for i in issues), issues
