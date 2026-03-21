"""Unit tests for claimed_task_ids, register_claim, release_claim."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from onward.execution import (
    register_claim,
    release_claim,
    claimed_task_ids,
    load_ongoing,
    _write_ongoing,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_ongoing_json(root: Path, active_runs: list) -> None:
    path = root / ".onward/ongoing.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": 1, "updated_at": "2026-01-01T00:00:00Z", "active_runs": active_runs}),
        encoding="utf-8",
    )


def _config_with_timeout(root: Path, minutes: int) -> None:
    """Write a minimal .onward.config.yaml with the given claim_timeout_minutes."""
    cfg = root / ".onward.config.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        f"version: 1\nwork:\n  claim_timeout_minutes: {minutes}\n",
        encoding="utf-8",
    )


def _default_config(root: Path) -> None:
    """Write a minimal .onward.config.yaml with default (no claim_timeout_minutes key)."""
    cfg = root / ".onward.config.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("version: 1\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# claimed_task_ids: empty / missing
# ---------------------------------------------------------------------------

def test_claimed_task_ids_missing_ongoing(tmp_path: Path):
    _default_config(tmp_path)
    result = claimed_task_ids(tmp_path)
    assert result == set()


def test_claimed_task_ids_empty_ongoing(tmp_path: Path):
    _default_config(tmp_path)
    _write_ongoing_json(tmp_path, [])
    result = claimed_task_ids(tmp_path)
    assert result == set()


def test_claimed_task_ids_no_scope_entries(tmp_path: Path):
    """Entries without scope (plain task runs) are not included in claimed set."""
    _default_config(tmp_path)
    _write_ongoing_json(tmp_path, [
        {"id": "RUN-001-TASK-001", "target": "TASK-001", "status": "running"},
    ])
    result = claimed_task_ids(tmp_path)
    assert result == set()


# ---------------------------------------------------------------------------
# claimed_task_ids: active entries with scope chunk / plan
# ---------------------------------------------------------------------------

def test_claimed_task_ids_chunk_scope(tmp_path: Path):
    _default_config(tmp_path)
    _write_ongoing_json(tmp_path, [
        {
            "id": "CLAIM-001-CHUNK-001",
            "target": "CHUNK-001",
            "scope": "chunk",
            "claimed_children": ["TASK-001", "TASK-002"],
            "pid": os.getpid(),
            "status": "running",
            "started_at": "2099-01-01T00:00:00Z",
        }
    ])
    result = claimed_task_ids(tmp_path)
    assert result == {"TASK-001", "TASK-002"}


def test_claimed_task_ids_plan_scope(tmp_path: Path):
    _default_config(tmp_path)
    _write_ongoing_json(tmp_path, [
        {
            "id": "CLAIM-001-CHUNK-002",
            "target": "CHUNK-002",
            "scope": "plan",
            "claimed_children": ["TASK-010", "TASK-011"],
            "pid": os.getpid(),
            "status": "running",
            "started_at": "2099-01-01T00:00:00Z",
        }
    ])
    result = claimed_task_ids(tmp_path)
    assert result == {"TASK-010", "TASK-011"}


def test_claimed_task_ids_union_of_multiple_entries(tmp_path: Path):
    _default_config(tmp_path)
    _write_ongoing_json(tmp_path, [
        {
            "id": "CLAIM-A-CHUNK-001",
            "target": "CHUNK-001",
            "scope": "chunk",
            "claimed_children": ["TASK-001", "TASK-002"],
            "pid": os.getpid(),
            "status": "running",
            "started_at": "2099-01-01T00:00:00Z",
        },
        {
            "id": "CLAIM-B-CHUNK-002",
            "target": "CHUNK-002",
            "scope": "plan",
            "claimed_children": ["TASK-003"],
            "pid": os.getpid(),
            "status": "running",
            "started_at": "2099-01-01T00:00:00Z",
        },
    ])
    result = claimed_task_ids(tmp_path)
    assert result == {"TASK-001", "TASK-002", "TASK-003"}


# ---------------------------------------------------------------------------
# claimed_task_ids: dead PID pruning
# ---------------------------------------------------------------------------

def test_claimed_task_ids_dead_pid_pruned(tmp_path: Path):
    _default_config(tmp_path)
    _write_ongoing_json(tmp_path, [
        {
            "id": "CLAIM-DEAD-CHUNK-001",
            "target": "CHUNK-001",
            "scope": "chunk",
            "claimed_children": ["TASK-001"],
            "pid": 99999999,
            "status": "running",
            "started_at": "2099-01-01T00:00:00Z",
        }
    ])
    with patch("os.kill", side_effect=ProcessLookupError):
        result = claimed_task_ids(tmp_path)

    assert result == set()
    # Entry should be pruned from ongoing.json
    ongoing = load_ongoing(tmp_path)
    claim_entries = [e for e in ongoing["active_runs"] if e.get("scope") in {"chunk", "plan"}]
    assert claim_entries == []


def test_claimed_task_ids_dead_pid_pruned_but_live_pid_kept(tmp_path: Path):
    _default_config(tmp_path)
    live_pid = os.getpid()
    _write_ongoing_json(tmp_path, [
        {
            "id": "CLAIM-DEAD",
            "target": "CHUNK-001",
            "scope": "chunk",
            "claimed_children": ["TASK-001"],
            "pid": 99999999,
            "status": "running",
            "started_at": "2099-01-01T00:00:00Z",
        },
        {
            "id": "CLAIM-LIVE",
            "target": "CHUNK-002",
            "scope": "chunk",
            "claimed_children": ["TASK-002"],
            "pid": live_pid,
            "status": "running",
            "started_at": "2099-01-01T00:00:00Z",
        },
    ])

    def _fake_kill(pid: int, sig: int) -> None:
        if pid == 99999999:
            raise ProcessLookupError
        # live_pid: do nothing (alive)

    with patch("os.kill", side_effect=_fake_kill):
        result = claimed_task_ids(tmp_path)

    assert result == {"TASK-002"}
    ongoing = load_ongoing(tmp_path)
    remaining_ids = [e["id"] for e in ongoing["active_runs"]]
    assert "CLAIM-LIVE" in remaining_ids
    assert "CLAIM-DEAD" not in remaining_ids


# ---------------------------------------------------------------------------
# claimed_task_ids: claim_timeout_minutes expiry
# ---------------------------------------------------------------------------

def test_claimed_task_ids_expired_by_timeout(tmp_path: Path):
    _config_with_timeout(tmp_path, 60)
    # started_at in the past (> 60 minutes ago)
    _write_ongoing_json(tmp_path, [
        {
            "id": "CLAIM-OLD",
            "target": "CHUNK-001",
            "scope": "chunk",
            "claimed_children": ["TASK-001"],
            "pid": os.getpid(),
            "status": "running",
            "started_at": "2020-01-01T00:00:00Z",
        }
    ])
    result = claimed_task_ids(tmp_path)
    assert result == set()
    ongoing = load_ongoing(tmp_path)
    claim_entries = [e for e in ongoing["active_runs"] if e.get("scope") in {"chunk", "plan"}]
    assert claim_entries == []


def test_claimed_task_ids_not_expired_within_timeout(tmp_path: Path):
    _config_with_timeout(tmp_path, 60)
    _write_ongoing_json(tmp_path, [
        {
            "id": "CLAIM-FRESH",
            "target": "CHUNK-001",
            "scope": "chunk",
            "claimed_children": ["TASK-001"],
            "pid": os.getpid(),
            "status": "running",
            "started_at": "2099-01-01T00:00:00Z",
        }
    ])
    result = claimed_task_ids(tmp_path)
    assert "TASK-001" in result


# ---------------------------------------------------------------------------
# claimed_task_ids: claim_timeout_minutes = 0 disables claiming
# ---------------------------------------------------------------------------

def test_claimed_task_ids_disabled_when_timeout_zero(tmp_path: Path):
    _config_with_timeout(tmp_path, 0)
    _write_ongoing_json(tmp_path, [
        {
            "id": "CLAIM-ACTIVE",
            "target": "CHUNK-001",
            "scope": "chunk",
            "claimed_children": ["TASK-001", "TASK-002"],
            "pid": os.getpid(),
            "status": "running",
            "started_at": "2099-01-01T00:00:00Z",
        }
    ])
    result = claimed_task_ids(tmp_path)
    assert result == set()


# ---------------------------------------------------------------------------
# register_claim / release_claim
# ---------------------------------------------------------------------------

def testregister_claim_adds_entry(tmp_path: Path):
    _default_config(tmp_path)
    _write_ongoing_json(tmp_path, [])
    register_claim(tmp_path, "CLAIM-X-CHUNK-001", "CHUNK-001", "chunk", ["TASK-001", "TASK-002"], 1234)
    ongoing = load_ongoing(tmp_path)
    entries = [e for e in ongoing["active_runs"] if e.get("id") == "CLAIM-X-CHUNK-001"]
    assert len(entries) == 1
    e = entries[0]
    assert e["scope"] == "chunk"
    assert e["claimed_children"] == ["TASK-001", "TASK-002"]
    assert e["pid"] == 1234
    assert e["target"] == "CHUNK-001"
    assert e["status"] == "running"
    assert "started_at" in e


def testrelease_claim_removes_entry(tmp_path: Path):
    _default_config(tmp_path)
    _write_ongoing_json(tmp_path, [])
    register_claim(tmp_path, "CLAIM-Y-CHUNK-001", "CHUNK-001", "chunk", ["TASK-001"], 1234)
    release_claim(tmp_path, "CLAIM-Y-CHUNK-001")
    ongoing = load_ongoing(tmp_path)
    entries = [e for e in ongoing["active_runs"] if e.get("id") == "CLAIM-Y-CHUNK-001"]
    assert entries == []


def testrelease_claim_leaves_other_entries(tmp_path: Path):
    _default_config(tmp_path)
    _write_ongoing_json(tmp_path, [])
    register_claim(tmp_path, "CLAIM-A", "CHUNK-001", "chunk", ["TASK-001"], 1)
    register_claim(tmp_path, "CLAIM-B", "CHUNK-002", "chunk", ["TASK-002"], 2)
    release_claim(tmp_path, "CLAIM-A")
    ongoing = load_ongoing(tmp_path)
    ids = [e["id"] for e in ongoing["active_runs"]]
    assert "CLAIM-A" not in ids
    assert "CLAIM-B" in ids
