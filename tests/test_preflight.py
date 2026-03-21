"""Tests for executor preflight (PATH / binary) before subprocess-backed runs."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from onward import cli
from onward.artifacts import must_find_by_id
from onward.execution import run_chunk_post_markdown_hook
from onward.preflight import preflight_executor_command
from tests.workspace_helpers import clear_post_task_shell


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0
    clear_post_task_shell(root)


def _set_executor(root: Path, command: str) -> None:
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    raw = raw.replace("  command: onward-exec", f'  command: "{command}"')
    config_path.write_text(raw, encoding="utf-8")


def test_preflight_disabled_ignores_missing_command() -> None:
    config = {"executor": {"enabled": False, "command": "no-such-binary-xx", "args": []}}
    assert preflight_executor_command(config) is None


@pytest.mark.parametrize("cmd", ["true", "false", "TRUE"])
def test_preflight_skips_shell_stub_commands(cmd: str) -> None:
    config = {"executor": {"enabled": True, "command": cmd, "args": []}}
    assert preflight_executor_command(config) is None


def test_preflight_skips_builtin_executor_command() -> None:
    assert preflight_executor_command({"executor": {"enabled": True, "command": "builtin", "args": []}}) is None
    assert preflight_executor_command({"executor": {"enabled": True, "command": "Builtin", "args": []}}) is None


def test_preflight_skips_when_executor_command_omitted_builtin_path() -> None:
    assert preflight_executor_command({"executor": {"enabled": True, "args": []}}) is None


def test_preflight_reports_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "definitely-not-an-executor"
    config = {"executor": {"enabled": True, "command": str(missing), "args": []}}
    err = preflight_executor_command(config)
    assert err is not None
    assert "does not exist" in err


def test_preflight_reports_missing_path_token() -> None:
    config = {"executor": {"enabled": True, "command": "no-such-onward-preflight-cmd-xyz", "args": []}}
    err = preflight_executor_command(config)
    assert err is not None
    assert "PATH" in err


def test_preflight_accepts_sys_executable() -> None:
    config = {"executor": {"enabled": True, "command": sys.executable, "args": ["-c", "pass"]}}
    assert preflight_executor_command(config) is None


def test_work_task_fails_fast_on_preflight(tmp_path: Path, capsys) -> None:
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "no-such-onward-preflight-cmd-xyz")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "not found on PATH" in out

    task_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-001-ship.md").read_text(encoding="utf-8")
    assert 'status: "open"' in task_raw


def test_review_plan_preflight_before_subprocess(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.delenv("TRAIN_REVIEW_RESPONSE", raising=False)
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    _set_executor(tmp_path, "no-such-onward-preflight-cmd-xyz")
    capsys.readouterr()

    code = cli.main(["review-plan", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "not found on PATH" in out
    assert "No reviews completed" in out


def test_post_chunk_markdown_preflight(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "no-such-onward-preflight-cmd-xyz")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    chunk = must_find_by_id(tmp_path, "CHUNK-001")
    ok, msg = run_chunk_post_markdown_hook(tmp_path, chunk)
    assert ok is False
    assert "PATH" in msg
