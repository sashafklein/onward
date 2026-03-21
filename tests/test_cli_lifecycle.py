"""Lifecycle errors and hints align with docs/LIFECYCLE.md (PLAN-010 TASK-009)."""

from pathlib import Path

import pytest

from onward import cli
from onward.artifacts import transition_status

from tests.workspace_helpers import clear_post_task_shell


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0
    clear_post_task_shell(root)


def _set_executor(root: Path, command: str) -> None:
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    raw = raw.replace("  command: onward-exec", f'  command: "{command}"')
    config_path.write_text(raw, encoding="utf-8")


def _new_task(tmp_path: Path) -> None:
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0


def test_transition_status_rejects_removed_start_action() -> None:
    with pytest.raises(ValueError, match="unknown transition target"):
        transition_status("open", "start")


def test_complete_when_already_completed_mentions_lifecycle(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    _new_task(tmp_path)
    capsys.readouterr()
    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    code = cli.main(["complete", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "docs/LIFECYCLE.md" in out
    assert "already completed" in out


def test_cancel_when_already_canceled_mentions_lifecycle(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _new_task(tmp_path)
    capsys.readouterr()
    assert cli.main(["cancel", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    code = cli.main(["cancel", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "docs/LIFECYCLE.md" in out
    assert "terminal" in out


def test_work_canceled_task_mentions_lifecycle(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    _new_task(tmp_path)
    capsys.readouterr()
    assert cli.main(["cancel", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "docs/LIFECYCLE.md" in out
    assert "canceled" in out


def test_work_open_without_start_succeeds(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    _new_task(tmp_path)
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "completed" in out


def test_chunk_work_failure_hints_chunk_stays_in_progress(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "false")
    _new_task(tmp_path)
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Stopping chunk work" in out
    assert "still in_progress" in out
    assert "docs/LIFECYCLE.md" in out
