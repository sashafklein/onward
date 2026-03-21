"""Integration tests for claim lifecycle: work_chunk, report, and next."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from onward import cli
from onward.execution import (
    register_claim,
    release_claim,
    claimed_task_ids,
    load_ongoing,
)
from tests.workspace_helpers import (
    clear_post_chunk_markdown,
    clear_post_task_markdown,
    clear_post_task_shell,
)


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------

def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0
    clear_post_task_shell(root)
    clear_post_task_markdown(root)
    clear_post_chunk_markdown(root)


def _set_python_ack_executor(root: Path) -> None:
    script = root / ".onward" / "ack_exec.py"
    script.write_text(
        'import json, os\n'
        'print(json.dumps({"onward_task_result": {"status": "completed", "schema_version": 1, '
        '"run_id": os.environ["ONWARD_RUN_ID"]}}))\n',
        encoding="utf-8",
    )
    config_path = root / ".onward.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    text = text.replace("  command: builtin", f"  command: {json.dumps(sys.executable)}", 1)
    text = text.replace("  args: []", "  args:\n    - .onward/ack_exec.py\n", 1)
    config_path.write_text(text, encoding="utf-8")


def _inject_claim(root: Path, task_ids: list[str], *, pid: int | None = None) -> str:
    """Inject a chunk-scope claim for the given task IDs; returns the claim run_id."""
    claim_id = "CLAIM-TEST-CHUNK-001"
    register_claim(
        root,
        claim_id,
        "CHUNK-001",
        "chunk",
        task_ids,
        pid if pid is not None else os.getpid(),
    )
    return claim_id


# ---------------------------------------------------------------------------
# TASK-070: work_chunk registers and releases claims
# ---------------------------------------------------------------------------

def test_work_chunk_releases_claim_on_completion(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_python_ack_executor(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    capsys.readouterr()
    assert code == 0

    ongoing = load_ongoing(tmp_path)
    claim_entries = [e for e in ongoing["active_runs"] if e.get("scope") in {"chunk", "plan"}]
    assert claim_entries == [], "claim should be released after work_chunk completes"


def test_work_chunk_releases_claim_on_task_failure(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    # Use 'false' as executor so task fails
    config_path = tmp_path / ".onward.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    text = text.replace("  command: builtin", "  command: false")
    config_path.write_text(text, encoding="utf-8")

    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    capsys.readouterr()
    assert code == 1

    ongoing = load_ongoing(tmp_path)
    claim_entries = [e for e in ongoing["active_runs"] if e.get("scope") in {"chunk", "plan"}]
    assert claim_entries == [], "claim should be released even when task fails"


# ---------------------------------------------------------------------------
# TASK-072: report and next respect claimed_ids
# ---------------------------------------------------------------------------

def test_report_excludes_claimed_tasks_from_upcoming(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    _inject_claim(tmp_path, ["TASK-001"])

    code = cli.main(["report", "--root", str(tmp_path), "--no-color"])
    out = capsys.readouterr().out
    assert code == 0

    # Upcoming section should NOT include TASK-001
    lines = out.splitlines()
    in_upcoming = False
    for line in lines:
        if "[Upcoming]" in line:
            in_upcoming = True
        elif line.startswith("[") and "]" in line:
            in_upcoming = False
        elif in_upcoming and "TASK-001" in line:
            pytest.fail(f"TASK-001 appeared in [Upcoming] but should be in [Claimed]: {line!r}")

    # Claimed section should include TASK-001
    assert "TASK-001" in out and "[Claimed]" in out


def test_report_no_claimed_section_when_no_claims(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path), "--no-color"])
    out = capsys.readouterr().out
    assert code == 0
    assert "[Claimed]" not in out
    assert "TASK-001" in out  # task appears in [Upcoming]


def test_next_skips_claimed_task(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "First"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Second"]) == 0
    capsys.readouterr()

    _inject_claim(tmp_path, ["TASK-001"])

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    # TASK-001 is claimed; TASK-002 should be selected instead
    assert "TASK-002" in out
    assert "TASK-001" not in out


def test_next_does_not_return_claimed_task(tmp_path: Path, capsys):
    """When all ready tasks are claimed, next never returns any of those tasks."""
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Only"]) == 0
    capsys.readouterr()

    _inject_claim(tmp_path, ["TASK-001"])

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    # TASK-001 must never be returned (it is claimed)
    assert "TASK-001" not in out


# ---------------------------------------------------------------------------
# TASK-073: stale claim (dead PID) is auto-cleaned on report invocation
# ---------------------------------------------------------------------------

def test_report_cleans_stale_claim_with_dead_pid(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    # Inject a claim with a dead PID
    register_claim(tmp_path, "CLAIM-STALE", "CHUNK-001", "chunk", ["TASK-001"], pid=99999999)

    with patch("os.kill", side_effect=ProcessLookupError):
        code = cli.main(["report", "--root", str(tmp_path), "--no-color"])
    out = capsys.readouterr().out
    assert code == 0

    # After report, the stale claim should be gone from ongoing.json
    ongoing = load_ongoing(tmp_path)
    stale = [e for e in ongoing["active_runs"] if e.get("id") == "CLAIM-STALE"]
    assert stale == [], "stale claim with dead PID should be pruned"

    # TASK-001 should appear in [Upcoming] (unclaimed after stale cleanup)
    assert "TASK-001" in out
    assert "[Claimed]" not in out
