"""Tests for Linear integration (onward linear push)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from onward import cli
from onward.linear import (
    LinearError,
    LinearIssue,
    WorkflowState,
    get_api_key,
    get_team_id,
    map_status_to_state,
)
from onward.cli_commands import _extract_plan_summary


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------


SAMPLE_STATES = [
    WorkflowState(id="s1", name="Backlog", category="backlog"),
    WorkflowState(id="s2", name="Todo", category="unstarted"),
    WorkflowState(id="s3", name="In Progress", category="started"),
    WorkflowState(id="s4", name="Done", category="completed"),
    WorkflowState(id="s5", name="Canceled", category="canceled"),
]


class TestMapStatusToState:
    def test_open_maps_to_unstarted(self):
        state = map_status_to_state("open", SAMPLE_STATES)
        assert state is not None
        assert state.category == "unstarted"

    def test_in_progress_maps_to_started(self):
        state = map_status_to_state("in_progress", SAMPLE_STATES)
        assert state is not None
        assert state.category == "started"

    def test_completed_maps_to_completed(self):
        state = map_status_to_state("completed", SAMPLE_STATES)
        assert state is not None
        assert state.category == "completed"

    def test_canceled_maps_to_canceled(self):
        state = map_status_to_state("canceled", SAMPLE_STATES)
        assert state is not None
        assert state.category == "canceled"

    def test_failed_maps_to_unstarted(self):
        state = map_status_to_state("failed", SAMPLE_STATES)
        assert state is not None
        assert state.category == "unstarted"

    def test_unknown_status_falls_back_to_unstarted(self):
        state = map_status_to_state("banana", SAMPLE_STATES)
        assert state is not None
        assert state.category == "unstarted"

    def test_empty_states_returns_none(self):
        assert map_status_to_state("open", []) is None


class TestGetApiKey:
    def test_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_abc123")
        assert get_api_key() == "lin_api_abc123"

    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)
        assert get_api_key() is None

    def test_returns_none_when_empty(self, monkeypatch):
        monkeypatch.setenv("LINEAR_API_KEY", "  ")
        assert get_api_key() is None


class TestGetTeamId:
    def test_reads_from_config(self):
        assert get_team_id({"linear": {"team_id": "abc-123"}}) == "abc-123"

    def test_returns_none_when_missing(self):
        assert get_team_id({}) is None

    def test_returns_none_when_empty(self):
        assert get_team_id({"linear": {"team_id": ""}}) is None

    def test_returns_none_when_not_dict(self):
        assert get_team_id({"linear": "bad"}) is None


# ---------------------------------------------------------------------------
# CLI integration tests (mocked HTTP)
# ---------------------------------------------------------------------------


def _init_workspace(tmp_path: Path) -> Path:
    """Set up a minimal Onward workspace and return the root."""
    cli.main(["init", "--root", str(tmp_path)])
    return tmp_path


def _write_config_with_linear(root: Path, team_id: str) -> None:
    path = root / ".onward.config.yaml"
    path.write_text(
        f"version: 1\nlinear:\n  team_id: \"{team_id}\"\n",
        encoding="utf-8",
    )


def _create_plan(root: Path, plan_id: str, title: str, status: str = "open", linear_id: str = "") -> None:
    plan_slug = title.lower().replace(" ", "-")[:30]
    plan_dir = root / ".onward" / "plans" / f"{plan_id}-{plan_slug}"
    plan_dir.mkdir(parents=True, exist_ok=True)
    meta_lines = [
        f'id: "{plan_id}"',
        'type: "plan"',
        'project: ""',
        f'title: "{title}"',
        f'status: "{status}"',
        'description: "test plan"',
        'priority: "medium"',
        'model: "opus"',
        'created_at: "2026-01-01T00:00:00Z"',
        'updated_at: "2026-01-01T00:00:00Z"',
    ]
    if linear_id:
        meta_lines.append(f'linear_id: "{linear_id}"')
    frontmatter = "\n".join(meta_lines)
    body = "# Summary\n\nTest plan summary.\n"
    (plan_dir / "plan.md").write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")


class TestLinearPushCLI:
    def test_missing_api_key(self, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)
        capsys.readouterr()

        rc = cli.main(["linear", "--root", str(root), "push"])
        assert rc == 1
        out = capsys.readouterr().out
        assert "LINEAR_API_KEY" in out

    def test_missing_team_id(self, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")
        capsys.readouterr()

        rc = cli.main(["linear", "--root", str(root), "push"])
        assert rc == 1
        out = capsys.readouterr().out
        assert "team_id" in out

    def test_dry_run_lists_plans(self, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        _create_plan(root, "PLAN-001", "First Plan")
        _create_plan(root, "PLAN-002", "Second Plan", linear_id="existing-id")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")
        capsys.readouterr()

        rc = cli.main(["linear", "--root", str(root), "push", "--dry-run"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "create" in out
        assert "PLAN-001" in out
        assert "update" in out
        assert "PLAN-002" in out
        assert "Dry run" in out

    @patch("onward.linear._graphql")
    def test_creates_issue_for_new_plan(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        _create_plan(root, "PLAN-001", "My New Plan")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        # Mock responses: first call = fetch_team_states, second = create_issue
        mock_graphql.side_effect = [
            # fetch_team_states
            {
                "team": {
                    "states": {
                        "nodes": [
                            {"id": "st-1", "name": "Todo", "type": "unstarted"},
                            {"id": "st-2", "name": "In Progress", "type": "started"},
                            {"id": "st-3", "name": "Done", "type": "completed"},
                            {"id": "st-4", "name": "Canceled", "type": "canceled"},
                        ]
                    }
                }
            },
            # create_issue
            {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue-uuid-123",
                        "identifier": "ENG-1",
                        "title": "My New Plan",
                        "url": "https://linear.app/team/issue/ENG-1",
                    },
                }
            },
        ]

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "push"])
        assert rc == 0

        out = capsys.readouterr().out
        assert "ENG-1" in out
        assert "1 created" in out

        # Verify linear_id was written back to frontmatter
        from onward.artifacts import parse_artifact
        plan_files = list((root / ".onward" / "plans").rglob("plan.md"))
        assert len(plan_files) == 1
        art = parse_artifact(plan_files[0])
        assert art.metadata["linear_id"] == "issue-uuid-123"
        assert art.metadata["linear_identifier"] == "ENG-1"

    @patch("onward.linear._graphql")
    def test_updates_state_for_linked_plan(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        _create_plan(root, "PLAN-001", "Existing Plan", status="completed", linear_id="issue-uuid-existing")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.side_effect = [
            # fetch_team_states
            {
                "team": {
                    "states": {
                        "nodes": [
                            {"id": "st-1", "name": "Todo", "type": "unstarted"},
                            {"id": "st-2", "name": "In Progress", "type": "started"},
                            {"id": "st-3", "name": "Done", "type": "completed"},
                        ]
                    }
                }
            },
            # get_issue (check existing)
            {
                "issue": {
                    "id": "issue-uuid-existing",
                    "identifier": "ENG-5",
                    "title": "Existing Plan",
                    "url": "https://linear.app/team/issue/ENG-5",
                    "state": {"id": "st-2", "name": "In Progress", "type": "started"},
                }
            },
            # update_issue_state
            {"issueUpdate": {"success": True}},
        ]

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "push"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "update" in out
        assert "Done" in out

    def test_no_plans_shows_message(self, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")
        capsys.readouterr()

        rc = cli.main(["linear", "--root", str(root), "push"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No plans found" in out


# ---------------------------------------------------------------------------
# _extract_plan_summary
# ---------------------------------------------------------------------------


class TestExtractPlanSummary:
    def test_extracts_summary(self):
        body = "# Summary\n\nThis is the summary.\n\n# Goals\n\n- foo\n"
        assert _extract_plan_summary(body) == "This is the summary."

    def test_skips_comments(self):
        body = "# Summary\n\n<!-- comment -->\nActual summary.\n\n# Goals\n"
        assert _extract_plan_summary(body) == "Actual summary."

    def test_empty_body(self):
        assert _extract_plan_summary("") == ""

    def test_no_summary_heading(self):
        assert _extract_plan_summary("# Goals\n\n- foo\n") == ""
