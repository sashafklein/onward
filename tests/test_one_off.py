"""Tests for the onward one-off command (standalone tasks without plan/chunk)."""

from __future__ import annotations

from pathlib import Path

from onward import cli
from onward.artifacts import collect_artifacts, find_by_id, validate_artifact
from onward.config import WorkspaceLayout, load_workspace_config

from tests.workspace_helpers import clear_post_task_shell, clear_post_task_markdown, clear_post_chunk_markdown


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def test_one_off_creates_task_file(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    result = cli.main(["one-off", "--root", str(tmp_path), "Fix button color"])
    assert result == 0
    out = capsys.readouterr().out
    assert "TASK-001" in out

    # Verify the file exists in one-offs/
    task_files = list((tmp_path / ".onward" / "one-offs").glob("TASK-001-*.md"))
    assert len(task_files) == 1

    # Verify frontmatter
    content = task_files[0].read_text(encoding="utf-8")
    assert 'plan: null' in content
    assert 'chunk: null' in content
    assert 'title: "Fix button color"' in content
    assert 'type: "task"' in content
    assert 'status: "open"' in content


def test_one_off_with_options(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    result = cli.main([
        "one-off", "--root", str(tmp_path),
        "Update docs",
        "--model", "opus",
        "--complexity", "low",
        "--description", "Update all docs",
        "--human",
    ])
    assert result == 0
    task_files = list((tmp_path / ".onward" / "one-offs").glob("TASK-001-*.md"))
    content = task_files[0].read_text(encoding="utf-8")
    assert 'model: "opus"' in content
    assert 'complexity: "low"' in content
    assert 'description: "Update all docs"' in content
    assert "human: true" in content


def test_one_off_appears_in_list(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    cli.main(["one-off", "--root", str(tmp_path), "Standalone task"])
    capsys.readouterr()

    result = cli.main(["list", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert result == 0
    assert "TASK-001" in out
    assert "Standalone task" in out


def test_one_off_appears_in_show(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    cli.main(["one-off", "--root", str(tmp_path), "Show me"])
    capsys.readouterr()

    result = cli.main(["show", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert result == 0
    assert "TASK-001" in out
    assert "Show me" in out


def test_one_off_shares_id_space_with_regular_tasks(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    # Create a regular plan+chunk+task first
    cli.main(["new", "--root", str(tmp_path), "plan", "P1"])
    cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C1"])
    cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Regular task"])
    capsys.readouterr()

    # Now create a one-off — should get TASK-002
    cli.main(["one-off", "--root", str(tmp_path), "One-off task"])
    out = capsys.readouterr().out
    assert "TASK-002" in out


def test_one_off_validation_allows_null_plan_chunk(tmp_path: Path):
    _init_workspace(tmp_path)
    cli.main(["one-off", "--root", str(tmp_path), "Valid task"])

    config = load_workspace_config(tmp_path)
    layout = WorkspaceLayout.from_config(tmp_path, config)
    task = find_by_id(layout, "TASK-001")
    assert task is not None
    issues = validate_artifact(task)
    assert not issues, f"Unexpected validation issues: {issues}"


def test_one_off_complete_lifecycle(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    cli.main(["one-off", "--root", str(tmp_path), "Complete me"])
    capsys.readouterr()

    # Complete the one-off task
    result = cli.main(["complete", "--root", str(tmp_path), "TASK-001"])
    assert result == 0

    config = load_workspace_config(tmp_path)
    layout = WorkspaceLayout.from_config(tmp_path, config)
    task = find_by_id(layout, "TASK-001")
    assert task is not None
    assert task.metadata["status"] == "completed"


def test_one_off_appears_in_recent(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    cli.main(["one-off", "--root", str(tmp_path), "Recent task"])
    cli.main(["complete", "--root", str(tmp_path), "TASK-001"])
    capsys.readouterr()

    result = cli.main(["recent", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert result == 0
    assert "TASK-001" in out


def test_one_off_mixed_with_regular_in_list(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    # Create regular artifacts
    cli.main(["new", "--root", str(tmp_path), "plan", "Plan A"])
    cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Chunk A"])
    cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Regular"])
    # Create one-off
    cli.main(["one-off", "--root", str(tmp_path), "One-off"])
    capsys.readouterr()

    result = cli.main(["list", "--root", str(tmp_path), "--type", "task"])
    out = capsys.readouterr().out
    assert result == 0
    assert "TASK-001" in out  # regular task
    assert "TASK-002" in out  # one-off task
