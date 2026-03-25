"""Tests for Linear integration (onward linear push / pull)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from onward import cli
from onward.linear import (
    LinearError,
    LinearIssue,
    LinearIssueFull,
    WorkflowState,
    get_api_key,
    get_stale_after,
    get_team_id,
    linear_priority_to_onward,
    linear_category_to_status,
    map_status_to_state,
    read_last_pull_time,
    should_auto_pull,
    write_last_pull_time,
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


def _create_plan(
    root: Path,
    plan_id: str,
    title: str,
    status: str = "open",
    linear_id: str = "",
    linear_synced_at: str = "",
    updated_at: str = "2026-01-01T00:00:00Z",
) -> None:
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
        f'updated_at: "{updated_at}"',
    ]
    if linear_id:
        meta_lines.append(f'linear_id: "{linear_id}"')
    if linear_synced_at:
        meta_lines.append(f'linear_synced_at: "{linear_synced_at}"')
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


# ---------------------------------------------------------------------------
# Pull-specific unit tests
# ---------------------------------------------------------------------------


class TestLinearPriorityMapping:
    def test_urgent_maps_to_high(self):
        assert linear_priority_to_onward(1) == "high"

    def test_high_maps_to_high(self):
        assert linear_priority_to_onward(2) == "high"

    def test_medium_maps_to_medium(self):
        assert linear_priority_to_onward(3) == "medium"

    def test_low_maps_to_low(self):
        assert linear_priority_to_onward(4) == "low"

    def test_none_maps_to_medium(self):
        assert linear_priority_to_onward(0) == "medium"

    def test_unknown_maps_to_medium(self):
        assert linear_priority_to_onward(99) == "medium"


class TestLinearCategoryToStatus:
    def test_unstarted(self):
        assert linear_category_to_status("unstarted") == "open"

    def test_started(self):
        assert linear_category_to_status("started") == "in_progress"

    def test_completed(self):
        assert linear_category_to_status("completed") == "completed"

    def test_canceled(self):
        assert linear_category_to_status("canceled") == "canceled"

    def test_backlog(self):
        assert linear_category_to_status("backlog") == "open"

    def test_unknown(self):
        assert linear_category_to_status("mystery") == "open"


class TestStaleAfter:
    def test_default_zero(self):
        assert get_stale_after({}) == 0

    def test_from_config(self):
        assert get_stale_after({"linear": {"stale_after": 15}}) == 15

    def test_negative_clamped(self):
        assert get_stale_after({"linear": {"stale_after": -5}}) == 0

    def test_non_numeric(self):
        assert get_stale_after({"linear": {"stale_after": "bad"}}) == 0

    def test_backward_compat_poll_interval(self):
        assert get_stale_after({"linear": {"poll_interval": 10}}) == 10

    def test_stale_after_wins_over_poll_interval(self):
        assert get_stale_after({"linear": {"stale_after": 20, "poll_interval": 10}}) == 20


class TestLastPullTimestamp:
    def test_write_and_read(self, tmp_path: Path):
        write_last_pull_time(tmp_path)
        ts = read_last_pull_time(tmp_path)
        assert ts is not None
        assert (datetime.now(timezone.utc) - ts).total_seconds() < 5

    def test_read_missing(self, tmp_path: Path):
        assert read_last_pull_time(tmp_path) is None


class TestShouldAutoPull:
    def test_not_configured(self, monkeypatch):
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)
        assert should_auto_pull({}, Path("/tmp/fake")) is False

    def test_no_last_pull(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("LINEAR_API_KEY", "key")
        config = {"linear": {"team_id": "t1", "poll_interval": 15}}
        assert should_auto_pull(config, tmp_path) is True

    def test_within_interval(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("LINEAR_API_KEY", "key")
        config = {"linear": {"team_id": "t1", "stale_after": 60}}
        write_last_pull_time(tmp_path)
        assert should_auto_pull(config, tmp_path) is False

    def test_stale_after_zero_always_pulls(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("LINEAR_API_KEY", "key")
        config = {"linear": {"team_id": "t1", "stale_after": 0}}
        write_last_pull_time(tmp_path)
        assert should_auto_pull(config, tmp_path) is True


# ---------------------------------------------------------------------------
# onward linear pull CLI tests
# ---------------------------------------------------------------------------


def _make_graphql_team_issues_response(issues: list[dict]) -> dict:
    return {
        "team": {
            "issues": {
                "nodes": issues,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
    }


class TestLinearPullCLI:
    def test_missing_api_key(self, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)
        capsys.readouterr()

        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 1
        out = capsys.readouterr().out
        assert "LINEAR_API_KEY" in out

    @patch("onward.linear._graphql")
    def test_updates_priority_from_linear(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        # synced_at == updated_at → no local edits since sync
        _create_plan(root, "PLAN-001", "My Plan", status="open", linear_id="issue-uuid-1",
                      linear_synced_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-1",
                "identifier": "ENG-1",
                "title": "My Plan",
                "url": "https://linear.app/ENG-1",
                "priority": 1,
                "sortOrder": 1.0,
                "description": "",
                "updatedAt": "2026-01-02T00:00:00Z",
                "state": {"type": "unstarted"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "priority: medium → high" in out
        assert "1 updated" in out

        from onward.artifacts import parse_artifact
        plan_files = list((root / ".onward" / "plans").rglob("plan.md"))
        art = parse_artifact(plan_files[0])
        assert art.metadata["priority"] == "high"
        assert art.metadata.get("linear_synced_at", "") != ""

    @patch("onward.linear._graphql")
    def test_creates_plan_from_new_linear_issue(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-new",
                "identifier": "ENG-99",
                "title": "Plan From Linear",
                "url": "https://linear.app/ENG-99",
                "priority": 2,
                "sortOrder": 1.0,
                "description": "Created by the CEO in Linear.",
                "updatedAt": "2026-01-02T00:00:00Z",
                "state": {"type": "started"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "ENG-99" in out
        assert "1 created" in out

        from onward.artifacts import parse_artifact
        plan_files = list((root / ".onward" / "plans").rglob("plan.md"))
        assert len(plan_files) == 1
        art = parse_artifact(plan_files[0])
        assert art.metadata["linear_id"] == "issue-uuid-new"
        assert art.metadata["linear_identifier"] == "ENG-99"
        assert art.metadata["priority"] == "high"
        assert art.metadata["status"] == "in_progress"
        assert art.metadata.get("linear_synced_at", "") != ""

    @patch("onward.linear._graphql")
    def test_skips_unprioritized_backlog(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-backlog",
                "identifier": "ENG-100",
                "title": "Vague Idea",
                "url": "https://linear.app/ENG-100",
                "priority": 0,
                "sortOrder": 99.0,
                "description": "",
                "updatedAt": "2026-01-01T00:00:00Z",
                "state": {"type": "backlog"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "0 created" in out

    @patch("onward.linear._graphql")
    def test_writes_last_pull_timestamp(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([])

        capsys.readouterr()
        cli.main(["linear", "--root", str(root), "pull"])
        ts = read_last_pull_time(root / ".onward")
        assert ts is not None

    @patch("onward.linear._graphql")
    def test_conflict_when_both_sides_changed(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        """When local was edited after last sync AND Linear differs, write conflict file."""
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        # synced at T1, but locally updated at T2 (after sync) → local edits exist
        _create_plan(root, "PLAN-001", "Conflicting Plan", status="open", linear_id="issue-uuid-1",
                      linear_synced_at="2026-01-01T00:00:00Z", updated_at="2026-01-02T00:00:00Z")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-1",
                "identifier": "ENG-1",
                "title": "Conflicting Plan",
                "url": "https://linear.app/ENG-1",
                "priority": 1,  # high — differs from local medium
                "sortOrder": 1.0,
                "description": "Linear description.",
                "updatedAt": "2026-01-03T00:00:00Z",
                "state": {"type": "unstarted"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 1  # conflicts return non-zero
        out = capsys.readouterr().out
        assert "CONFLICT" in out
        assert "1 conflicts" in out

        # Verify plan-linear.md was written
        plan_dir = list((root / ".onward" / "plans").glob("PLAN-001-*"))[0]
        conflict_file = plan_dir / "plan-linear.md"
        assert conflict_file.exists()
        content = conflict_file.read_text()
        assert "Linear conflict" in content
        assert "ENG-1" in content
        assert "Linear description." in content

        # Verify plan.md was NOT modified
        from onward.artifacts import parse_artifact
        art = parse_artifact(plan_dir / "plan.md")
        assert art.metadata["priority"] == "medium"  # unchanged

    @patch("onward.linear._graphql")
    def test_no_conflict_when_only_linear_changed(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        """When local was NOT edited since sync, Linear wins without conflict."""
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        # synced_at == updated_at → no local edits
        _create_plan(root, "PLAN-001", "Clean Plan", status="open", linear_id="issue-uuid-1",
                      linear_synced_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-1",
                "identifier": "ENG-1",
                "title": "Clean Plan",
                "url": "https://linear.app/ENG-1",
                "priority": 1,
                "sortOrder": 1.0,
                "description": "",
                "updatedAt": "2026-01-02T00:00:00Z",
                "state": {"type": "unstarted"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "CONFLICT" not in out
        assert "1 updated" in out

        # No conflict file
        plan_dir = list((root / ".onward" / "plans").glob("PLAN-001-*"))[0]
        assert not (plan_dir / "plan-linear.md").exists()

    @patch("onward.linear._graphql")
    def test_pull_syncs_title_and_description(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        """Pull should update title and description when Linear values changed."""
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        _create_plan(root, "PLAN-001", "Old Title", status="open", linear_id="issue-uuid-1",
                      linear_synced_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-1",
                "identifier": "ENG-1",
                "title": "New Title From Linear",
                "url": "https://linear.app/ENG-1",
                "priority": 3,
                "sortOrder": 1.0,
                "description": "Updated description from CEO",
                "updatedAt": "2026-01-02T00:00:00Z",
                "state": {"type": "unstarted"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "1 updated" in out
        assert "title:" in out
        assert "body updated" in out

        plan_dir = list((root / ".onward" / "plans").glob("PLAN-001-*"))[0]
        plan_text = (plan_dir / "plan.md").read_text()
        assert "New Title From Linear" in plan_text

        from onward.artifacts import parse_artifact
        art = parse_artifact(plan_dir / "plan.md")
        assert art.metadata["title"] == "New Title From Linear"
        assert "Updated description from CEO" in art.body

    @patch("onward.linear._graphql")
    def test_pull_body_not_overwritten_when_linear_empty(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        """If Linear description is empty, local body should not be wiped out."""
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        _create_plan(root, "PLAN-001", "My Plan", status="open", linear_id="issue-uuid-1",
                      linear_synced_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-1",
                "identifier": "ENG-1",
                "title": "My Plan",
                "url": "https://linear.app/ENG-1",
                "priority": 3,
                "sortOrder": 1.0,
                "description": "",
                "updatedAt": "2026-01-02T00:00:00Z",
                "state": {"type": "unstarted"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 0

        from onward.artifacts import parse_artifact
        plan_dir = list((root / ".onward" / "plans").glob("PLAN-001-*"))[0]
        art = parse_artifact(plan_dir / "plan.md")
        assert "Test plan summary" in art.body

    @patch("onward.linear._graphql")
    def test_conflict_when_no_synced_at(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        """Plans that predate Linear integration (no linear_synced_at) conflict if Linear differs."""
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        # Has linear_id but no linear_synced_at (pre-integration)
        _create_plan(root, "PLAN-001", "Legacy Plan", status="open", linear_id="issue-uuid-1")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-1",
                "identifier": "ENG-1",
                "title": "Legacy Plan",
                "url": "https://linear.app/ENG-1",
                "priority": 1,
                "sortOrder": 1.0,
                "description": "",
                "updatedAt": "2026-01-02T00:00:00Z",
                "state": {"type": "unstarted"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 1
        out = capsys.readouterr().out
        assert "CONFLICT" in out


# ---------------------------------------------------------------------------
# Auto-pull in roadmap
# ---------------------------------------------------------------------------


class TestRoadmapAutoPull:
    @patch("onward.linear._graphql")
    def test_roadmap_auto_pulls_when_configured(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        config_path = root / ".onward.config.yaml"
        config_path.write_text(
            'version: 1\nlinear:\n  team_id: "team-123"\n  stale_after: 0\n',
            encoding="utf-8",
        )
        _create_plan(root, "PLAN-001", "Existing Plan", status="open", linear_id="issue-uuid-1",
                      linear_synced_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-1",
                "identifier": "ENG-1",
                "title": "Existing Plan",
                "url": "https://linear.app/ENG-1",
                "priority": 1,
                "sortOrder": 1.0,
                "description": "",
                "updatedAt": "2026-01-02T00:00:00Z",
                "state": {"type": "unstarted"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["roadmap", "--root", str(root)])
        assert rc == 0
        out = capsys.readouterr().out
        # The auto-pull should have updated priority and shown a sync note
        assert "synced from Linear" in out or "Existing Plan" in out

    def test_roadmap_skips_pull_without_config(self, tmp_path: Path, capsys, monkeypatch):
        root = _init_workspace(tmp_path)
        _create_plan(root, "PLAN-001", "My Plan")
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)
        capsys.readouterr()

        rc = cli.main(["roadmap", "--root", str(root)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "synced from Linear" not in out


# ---------------------------------------------------------------------------
# linear_sort_order syncing
# ---------------------------------------------------------------------------


class TestLinearSortOrderPull:
    @patch("onward.linear._graphql")
    def test_created_plan_includes_sort_order(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        """New plans imported from Linear should store linear_sort_order."""
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-new",
                "identifier": "ENG-50",
                "title": "Sorted Plan",
                "url": "https://linear.app/ENG-50",
                "priority": 2,
                "sortOrder": 42.5,
                "description": "Has sort order.",
                "updatedAt": "2026-01-02T00:00:00Z",
                "state": {"type": "unstarted"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 0

        from onward.artifacts import parse_artifact
        plan_files = list((root / ".onward" / "plans").rglob("plan.md"))
        assert len(plan_files) == 1
        art = parse_artifact(plan_files[0])
        assert art.metadata["linear_sort_order"] == 42.5

    @patch("onward.linear._graphql")
    def test_updated_plan_syncs_sort_order(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        """Existing plans should get sort_order updated on pull."""
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        _create_plan(root, "PLAN-001", "My Plan", status="open", linear_id="issue-uuid-1",
                      linear_synced_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-1",
                "identifier": "ENG-1",
                "title": "My Plan",
                "url": "https://linear.app/ENG-1",
                "priority": 3,
                "sortOrder": 7.25,
                "description": "",
                "updatedAt": "2026-01-02T00:00:00Z",
                "state": {"type": "unstarted"},
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 0

        from onward.artifacts import parse_artifact
        plan_files = list((root / ".onward" / "plans").rglob("plan.md"))
        art = parse_artifact(plan_files[0])
        assert art.metadata["linear_sort_order"] == 7.25

    @patch("onward.linear._graphql")
    def test_sort_order_only_change_triggers_update(self, mock_graphql, tmp_path: Path, capsys, monkeypatch):
        """When only sort_order changes (priority/status same), plan should still update."""
        root = _init_workspace(tmp_path)
        _write_config_with_linear(root, "team-123")
        _create_plan(root, "PLAN-001", "My Plan", status="open", linear_id="issue-uuid-1",
                      linear_synced_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")

        mock_graphql.return_value = _make_graphql_team_issues_response([
            {
                "id": "issue-uuid-1",
                "identifier": "ENG-1",
                "title": "My Plan",
                "url": "https://linear.app/ENG-1",
                "priority": 3,  # medium → same as default
                "sortOrder": 99.0,
                "description": "",
                "updatedAt": "2026-01-02T00:00:00Z",
                "state": {"type": "unstarted"},  # open → same
            }
        ])

        capsys.readouterr()
        rc = cli.main(["linear", "--root", str(root), "pull"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "1 updated" in out

        from onward.artifacts import parse_artifact
        plan_files = list((root / ".onward" / "plans").rglob("plan.md"))
        art = parse_artifact(plan_files[0])
        assert art.metadata["linear_sort_order"] == 99.0


# ---------------------------------------------------------------------------
# Priority-aware ordering: select_next_artifact and plan_sort_key
# ---------------------------------------------------------------------------


class TestPlanSortKey:
    def test_high_before_medium(self):
        from onward.artifacts import plan_sort_key, Artifact
        high = Artifact(file_path=Path("a"), body="", metadata={"id": "PLAN-002", "priority": "high"})
        medium = Artifact(file_path=Path("b"), body="", metadata={"id": "PLAN-001", "priority": "medium"})
        assert plan_sort_key(high) < plan_sort_key(medium)

    def test_sort_order_breaks_priority_tie(self):
        from onward.artifacts import plan_sort_key, Artifact
        first = Artifact(file_path=Path("a"), body="", metadata={"id": "PLAN-002", "priority": "high", "linear_sort_order": 1.0})
        second = Artifact(file_path=Path("b"), body="", metadata={"id": "PLAN-001", "priority": "high", "linear_sort_order": 5.0})
        assert plan_sort_key(first) < plan_sort_key(second)

    def test_no_sort_order_sorts_last_within_tier(self):
        from onward.artifacts import plan_sort_key, Artifact
        with_order = Artifact(file_path=Path("a"), body="", metadata={"id": "PLAN-002", "priority": "medium", "linear_sort_order": 100.0})
        without = Artifact(file_path=Path("b"), body="", metadata={"id": "PLAN-001", "priority": "medium"})
        assert plan_sort_key(with_order) < plan_sort_key(without)

    def test_id_breaks_full_tie(self):
        from onward.artifacts import plan_sort_key, Artifact
        a = Artifact(file_path=Path("a"), body="", metadata={"id": "PLAN-001", "priority": "medium"})
        b = Artifact(file_path=Path("b"), body="", metadata={"id": "PLAN-002", "priority": "medium"})
        assert plan_sort_key(a) < plan_sort_key(b)


class TestSelectNextArtifactPriority:
    def _make_artifact(self, id: str, type: str, status: str, **extra) -> "Artifact":
        from onward.artifacts import Artifact
        meta = {"id": id, "type": type, "status": status, "title": id, "created_at": "", "updated_at": ""}
        meta.update(extra)
        return Artifact(file_path=Path(f"/fake/{id}.md"), body="", metadata=meta)

    def test_prefers_task_in_high_priority_plan(self):
        from onward.artifacts import select_next_artifact
        plan_high = self._make_artifact("PLAN-001", "plan", "in_progress", priority="high", linear_sort_order=1.0)
        plan_low = self._make_artifact("PLAN-002", "plan", "in_progress", priority="low", linear_sort_order=1.0)
        chunk_h = self._make_artifact("CHUNK-001", "chunk", "in_progress", plan="PLAN-001")
        chunk_l = self._make_artifact("CHUNK-002", "chunk", "in_progress", plan="PLAN-002")
        task_low = self._make_artifact("TASK-001", "task", "open", plan="PLAN-002", chunk="CHUNK-002", human=False)
        task_high = self._make_artifact("TASK-002", "task", "open", plan="PLAN-001", chunk="CHUNK-001", human=False)

        result = select_next_artifact([plan_high, plan_low, chunk_h, chunk_l, task_low, task_high])
        assert result is not None
        assert result.metadata["id"] == "TASK-002"

    def test_prefers_lower_sort_order_within_same_priority(self):
        from onward.artifacts import select_next_artifact
        plan_a = self._make_artifact("PLAN-001", "plan", "in_progress", priority="high", linear_sort_order=10.0)
        plan_b = self._make_artifact("PLAN-002", "plan", "in_progress", priority="high", linear_sort_order=1.0)
        chunk_a = self._make_artifact("CHUNK-001", "chunk", "in_progress", plan="PLAN-001")
        chunk_b = self._make_artifact("CHUNK-002", "chunk", "in_progress", plan="PLAN-002")
        task_a = self._make_artifact("TASK-001", "task", "open", plan="PLAN-001", chunk="CHUNK-001", human=False)
        task_b = self._make_artifact("TASK-002", "task", "open", plan="PLAN-002", chunk="CHUNK-002", human=False)

        result = select_next_artifact([plan_a, plan_b, chunk_a, chunk_b, task_a, task_b])
        assert result is not None
        assert result.metadata["id"] == "TASK-002"

    def test_in_progress_still_beats_priority(self):
        """Tasks in an in-progress chunk/plan still rank above non-in-progress, even if lower priority."""
        from onward.artifacts import select_next_artifact
        plan_high = self._make_artifact("PLAN-001", "plan", "open", priority="high")
        plan_low = self._make_artifact("PLAN-002", "plan", "in_progress", priority="low")
        chunk_h = self._make_artifact("CHUNK-001", "chunk", "open", plan="PLAN-001")
        chunk_l = self._make_artifact("CHUNK-002", "chunk", "in_progress", plan="PLAN-002")
        task_high = self._make_artifact("TASK-001", "task", "open", plan="PLAN-001", chunk="CHUNK-001", human=False)
        task_low = self._make_artifact("TASK-002", "task", "open", plan="PLAN-002", chunk="CHUNK-002", human=False)

        result = select_next_artifact([plan_high, plan_low, chunk_h, chunk_l, task_high, task_low])
        assert result is not None
        assert result.metadata["id"] == "TASK-002"

    def test_open_plans_sorted_by_priority(self):
        """When no ready tasks or chunks, open plans are returned in priority order."""
        from onward.artifacts import select_next_artifact
        plan_low = self._make_artifact("PLAN-001", "plan", "open", priority="low")
        plan_high = self._make_artifact("PLAN-002", "plan", "open", priority="high")

        result = select_next_artifact([plan_low, plan_high])
        assert result is not None
        assert result.metadata["id"] == "PLAN-002"
