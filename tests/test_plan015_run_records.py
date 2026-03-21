"""Tests for PLAN-015: run directory layout, backward compat, streaming, git diff, and token parsing."""
from __future__ import annotations

import json
import subprocess
import threading
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from onward.executor import ExecutorResult, TaskContext
from onward.executor_builtin import _tee_stream, extract_token_usage
from onward.util import compute_files_changed, get_head_sha


# ---------------------------------------------------------------------------
# 1. Run directory layout
# ---------------------------------------------------------------------------


def _make_workspace(tmp_path: Path) -> None:
    from onward import cli
    from tests.workspace_helpers import clear_post_task_shell

    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    clear_post_task_shell(tmp_path)
    config_path = tmp_path / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    config_path.write_text(raw.replace("  command: builtin", '  command: "true"'), encoding="utf-8")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0


def test_prepare_task_run_creates_per_task_directory(tmp_path: Path, capsys: Any) -> None:
    """New runs use runs/TASK-XXX/info-*.json layout."""
    _make_workspace(tmp_path)
    capsys.readouterr()
    from onward import cli

    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0

    task_dir = tmp_path / ".onward/runs/TASK-001"
    assert task_dir.is_dir(), "task directory should exist"
    info_files = list(task_dir.glob("info-*.json"))
    assert len(info_files) == 1, "one info-*.json should be created"
    summary_files = list(task_dir.glob("summary-*.log"))
    assert len(summary_files) == 1, "one summary-*.log should be created"

    rec = json.loads(info_files[0].read_text(encoding="utf-8"))
    assert rec["status"] == "completed"
    assert rec["target"] == "TASK-001"
    assert rec["id"].startswith("RUN-")
    assert "TASK-001" in rec["id"]
    assert rec["log_path"].startswith(".onward/runs/TASK-001/summary-")


@patch("onward.executor_builtin.subprocess.Popen")
def test_builtin_executor_creates_output_log(mock_popen: MagicMock, tmp_path: Path, capsys: Any) -> None:
    """BuiltinExecutor creates output-*.log and streams both stdout/stderr into it."""
    from tests.workspace_helpers import clear_post_task_shell, clear_post_task_markdown, clear_post_chunk_markdown

    class _FakeProc:
        stdout = _FakePipe(["hello from stdout\n"])
        stderr = _FakePipe(["hello from stderr\n"])
        def wait(self) -> int:
            return 0

    mock_popen.return_value = _FakeProc()

    from onward import cli
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    clear_post_task_shell(tmp_path)
    clear_post_task_markdown(tmp_path)
    clear_post_chunk_markdown(tmp_path)
    config_path = tmp_path / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    config_path.write_text(raw, encoding="utf-8")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "B"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "T"]) == 0
    capsys.readouterr()

    with patch("onward.executor_builtin.shutil.which", lambda _: "/bin/claude"):
        assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0

    task_dir = tmp_path / ".onward/runs/TASK-001"
    output_files = list(task_dir.glob("output-*.log"))
    assert len(output_files) == 1, "BuiltinExecutor should create output-*.log"
    content = output_files[0].read_text(encoding="utf-8")
    assert "hello from stdout" in content
    assert "hello from stderr" in content


def test_retry_creates_second_run_triple(tmp_path: Path, capsys: Any) -> None:
    """A retried task gets a second run triple; run_count reaches 2."""
    import time
    from onward import cli
    from tests.workspace_helpers import clear_post_task_shell

    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    clear_post_task_shell(tmp_path)
    config_path = tmp_path / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    config_path.write_text(raw.replace("  command: builtin", '  command: "false"'), encoding="utf-8")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 1
    task_dir = tmp_path / ".onward/runs/TASK-001"
    assert len(list(task_dir.glob("info-*.json"))) >= 1

    assert cli.main(["retry", "--root", str(tmp_path), "TASK-001"]) == 0
    time.sleep(1.1)
    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 1

    info_files = list(task_dir.glob("info-*.json"))
    assert len(info_files) == 2, "two runs should create two info files"
    summary_files = list(task_dir.glob("summary-*.log"))
    assert len(summary_files) == 2
    for f in info_files:
        rec = json.loads(f.read_text(encoding="utf-8"))
        assert rec["target"] == "TASK-001"
        assert rec["status"] == "failed"


def test_run_record_has_files_changed_and_token_usage_keys(tmp_path: Path, capsys: Any) -> None:
    """info-*.json always contains files_changed and token_usage keys."""
    _make_workspace(tmp_path)
    capsys.readouterr()
    from onward import cli

    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0

    run_file = next((tmp_path / ".onward/runs/TASK-001").glob("info-*.json"))
    rec = json.loads(run_file.read_text(encoding="utf-8"))
    assert "files_changed" in rec
    assert isinstance(rec["files_changed"], list)
    assert "token_usage" in rec


# ---------------------------------------------------------------------------
# 2. Backward compat: collect_runs_for_target finds legacy flat files
# ---------------------------------------------------------------------------


def test_collect_runs_for_target_finds_legacy_flat_files(tmp_path: Path) -> None:
    """collect_runs_for_target returns legacy RUN-*-TASK-XXX.json files."""
    from onward.execution import collect_runs_for_target

    runs_dir = tmp_path / ".onward/runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    legacy_rec = {
        "id": "RUN-2026-01-01T00-00-00Z-TASK-001",
        "type": "run",
        "target": "TASK-001",
        "status": "completed",
        "model": "opus",
        "executor": "true",
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T00:01:00Z",
        "log_path": ".onward/runs/x.log",
        "error": "",
    }
    (runs_dir / "RUN-2026-01-01T00-00-00Z-TASK-001.json").write_text(
        json.dumps(legacy_rec), encoding="utf-8"
    )

    results = collect_runs_for_target(tmp_path, "TASK-001")
    assert len(results) == 1
    assert results[0]["id"] == "RUN-2026-01-01T00-00-00Z-TASK-001"


def test_collect_runs_for_target_merges_new_and_legacy(tmp_path: Path) -> None:
    """collect_runs_for_target merges both layouts sorted by started_at (newest first)."""
    from onward.execution import collect_runs_for_target
    from onward.util import dump_run_json_record

    runs_dir = tmp_path / ".onward/runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    legacy_rec = {
        "id": "RUN-2026-01-01T00-00-00Z-TASK-001",
        "type": "run",
        "target": "TASK-001",
        "status": "completed",
        "model": "opus",
        "executor": "true",
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T00:01:00Z",
        "log_path": ".onward/runs/x.log",
        "error": "",
    }
    (runs_dir / "RUN-2026-01-01T00-00-00Z-TASK-001.json").write_text(
        json.dumps(legacy_rec), encoding="utf-8"
    )

    task_dir = runs_dir / "TASK-001"
    task_dir.mkdir()
    new_rec = {
        "id": "RUN-2026-03-01T00-00-00Z-TASK-001",
        "type": "run",
        "target": "TASK-001",
        "status": "completed",
        "model": "sonnet",
        "executor": "builtin",
        "started_at": "2026-03-01T00:00:00Z",
        "finished_at": "2026-03-01T00:01:00Z",
        "log_path": ".onward/runs/TASK-001/summary-2026-03-01T00-00-00Z.log",
        "error": "",
        "files_changed": [],
        "token_usage": None,
    }
    (task_dir / "info-2026-03-01T00-00-00Z.json").write_text(
        dump_run_json_record(new_rec), encoding="utf-8"
    )

    results = collect_runs_for_target(tmp_path, "TASK-001")
    assert len(results) == 2
    assert results[0]["id"] == "RUN-2026-03-01T00-00-00Z-TASK-001"
    assert results[1]["id"] == "RUN-2026-01-01T00-00-00Z-TASK-001"


def test_latest_run_for_returns_newest_across_both_layouts(tmp_path: Path) -> None:
    """latest_run_for returns the newest run regardless of layout."""
    from onward.execution import latest_run_for
    from onward.util import dump_run_json_record

    runs_dir = tmp_path / ".onward/runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "RUN-2026-01-01T00-00-00Z-TASK-001.json").write_text(
        json.dumps({
            "id": "RUN-2026-01-01T00-00-00Z-TASK-001",
            "type": "run",
            "target": "TASK-001",
            "status": "completed",
            "model": "opus",
            "executor": "true",
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:01:00Z",
            "log_path": ".onward/runs/x.log",
            "error": "",
        }),
        encoding="utf-8",
    )
    task_dir = runs_dir / "TASK-001"
    task_dir.mkdir()
    new_rec = {
        "id": "RUN-2026-06-01T00-00-00Z-TASK-001",
        "type": "run",
        "target": "TASK-001",
        "status": "completed",
        "model": "sonnet",
        "executor": "builtin",
        "started_at": "2026-06-01T00:00:00Z",
        "finished_at": "2026-06-01T00:01:00Z",
        "log_path": ".onward/runs/TASK-001/summary-2026-06-01T00-00-00Z.log",
        "error": "",
        "files_changed": [],
        "token_usage": None,
    }
    (task_dir / "info-2026-06-01T00-00-00Z.json").write_text(
        dump_run_json_record(new_rec), encoding="utf-8"
    )

    latest = latest_run_for(tmp_path, "TASK-001")
    assert latest is not None
    assert latest["id"] == "RUN-2026-06-01T00-00-00Z-TASK-001"


# ---------------------------------------------------------------------------
# 3. Streaming write: _tee_stream with file_out writes every line
# ---------------------------------------------------------------------------


class _FakePipe:
    def __init__(self, lines: list[str]) -> None:
        self._lines = list(lines)
        self._i = 0

    def readline(self) -> str:
        if self._i < len(self._lines):
            s = self._lines[self._i]
            self._i += 1
            return s if s.endswith("\n") else f"{s}\n"
        return ""

    def close(self) -> None:
        pass


def test_tee_stream_writes_all_lines_to_file_out() -> None:
    """_tee_stream writes every line to file_out and flushes."""
    lines = ["line1", "line2", "line3"]
    pipe = _FakePipe(lines)
    tee_to = StringIO()
    file_out = StringIO()

    _tee_stream(pipe, tee_to, [], file_out=file_out)

    written = file_out.getvalue()
    for line in lines:
        assert line in written
    assert tee_to.getvalue() == written


def test_tee_stream_without_file_out_unchanged() -> None:
    """_tee_stream with no file_out writes only to tee_to (existing behaviour)."""
    pipe = _FakePipe(["hello", "world"])
    tee_to = StringIO()
    buffer: list[str] = []

    _tee_stream(pipe, tee_to, buffer)

    assert "hello" in tee_to.getvalue()
    assert "world" in tee_to.getvalue()
    assert len(buffer) == 2


def test_tee_stream_file_lock_is_used_when_provided() -> None:
    """_tee_stream uses the provided lock (context manager) when writing to file_out."""
    acquire_count = 0

    class _CountingLock:
        def __enter__(self) -> "_CountingLock":
            nonlocal acquire_count
            acquire_count += 1
            return self

        def __exit__(self, *_: Any) -> None:
            pass

    pipe = _FakePipe(["a", "b"])
    file_out = StringIO()
    lock = _CountingLock()
    _tee_stream(pipe, StringIO(), [], file_out=file_out, file_lock=lock)  # type: ignore[arg-type]

    assert acquire_count == 2, "lock should be acquired once per line"


# ---------------------------------------------------------------------------
# 4. Git diff helpers
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True)


def _git_commit(path: Path, message: str = "commit") -> None:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message, "--allow-empty"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def test_get_head_sha_returns_sha_in_git_repo(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _git_commit(tmp_path, "initial")
    sha = get_head_sha(tmp_path)
    assert len(sha) == 40
    assert sha.isalnum()


def test_get_head_sha_returns_empty_outside_git(tmp_path: Path) -> None:
    sha = get_head_sha(tmp_path)
    assert sha == ""


def test_compute_files_changed_empty_before_sha(tmp_path: Path) -> None:
    result = compute_files_changed(tmp_path, "")
    assert result == []


def test_compute_files_changed_detects_new_file(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _git_commit(tmp_path, "initial")
    before_sha = get_head_sha(tmp_path)
    assert before_sha

    new_file = tmp_path / "foo.txt"
    new_file.write_text("hello", encoding="utf-8")
    _git_commit(tmp_path, "add foo")

    changed = compute_files_changed(tmp_path, before_sha)
    assert "foo.txt" in changed


def test_compute_files_changed_returns_empty_when_no_commits(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _git_commit(tmp_path, "initial")
    sha = get_head_sha(tmp_path)
    changed = compute_files_changed(tmp_path, sha)
    assert changed == []


def test_compute_files_changed_returns_empty_on_git_failure(tmp_path: Path) -> None:
    result = compute_files_changed(tmp_path, "nonexistent-sha-abc123")
    assert result == []


# ---------------------------------------------------------------------------
# 5. Token usage parser
# ---------------------------------------------------------------------------


def test_extract_token_usage_ndjson_format() -> None:
    """Parses NDJSON line with usage field."""
    stderr = 'some preamble\n{"usage": {"input_tokens": 1234, "output_tokens": 5678}}\n'
    result = extract_token_usage(stderr)
    assert result is not None
    assert result["input_tokens"] == 1234
    assert result["output_tokens"] == 5678
    assert result["total_tokens"] == 6912


def test_extract_token_usage_plain_text_regex() -> None:
    """Parses plain-text summary line."""
    stderr = "Task complete.\nInput tokens: 1000, Output tokens: 2000\n"
    result = extract_token_usage(stderr)
    assert result is not None
    assert result["input_tokens"] == 1000
    assert result["output_tokens"] == 2000
    assert result["total_tokens"] == 3000


def test_extract_token_usage_returns_none_for_unrecognized() -> None:
    result = extract_token_usage("no tokens here\njust plain text")
    assert result is None


def test_extract_token_usage_returns_none_for_empty() -> None:
    result = extract_token_usage("")
    assert result is None


def test_extract_token_usage_returns_none_on_malformed_json() -> None:
    result = extract_token_usage("{bad json\n")
    assert result is None


def test_extract_token_usage_prefers_last_matching_line() -> None:
    """Scans bottom-up; last matching JSON line wins."""
    stderr = (
        '{"usage": {"input_tokens": 100, "output_tokens": 200}}\n'
        "some text\n"
        '{"usage": {"input_tokens": 999, "output_tokens": 888}}\n'
    )
    result = extract_token_usage(stderr)
    assert result is not None
    assert result["input_tokens"] == 999


# ---------------------------------------------------------------------------
# 6. Ack schema v3 with token_usage
# ---------------------------------------------------------------------------


def test_ack_v3_token_usage_parsed_from_ack() -> None:
    """Ack v3 token_usage is included in parse_task_result output."""
    from onward.executor_ack import parse_task_result

    ack = {
        "onward_task_result": {
            "schema_version": 3,
            "status": "completed",
            "token_usage": {"input_tokens": 500, "output_tokens": 300, "total_tokens": 800},
        }
    }
    result = parse_task_result(ack)
    assert result["token_usage"] == {"input_tokens": 500, "output_tokens": 300, "total_tokens": 800}


def test_ack_v2_without_token_usage_returns_none() -> None:
    """v2 ack without token_usage yields token_usage=None."""
    from onward.executor_ack import parse_task_result

    ack = {
        "onward_task_result": {
            "schema_version": 2,
            "status": "completed",
        }
    }
    result = parse_task_result(ack)
    assert result["token_usage"] is None


def test_ack_v3_validated_and_accepted() -> None:
    """Schema version 3 acks pass validation."""
    from onward.executor_ack import find_task_success_ack

    line = json.dumps({
        "onward_task_result": {
            "schema_version": 3,
            "status": "completed",
            "run_id": "RUN-test-TASK-001",
        }
    })
    found, err, obj = find_task_success_ack(line, "", "RUN-test-TASK-001")
    assert found, f"expected found but got err: {err}"
    assert obj is not None


def test_executor_result_token_usage_defaults_to_none() -> None:
    """ExecutorResult.token_usage defaults to None for backward compat."""
    result = ExecutorResult(
        task_id="TASK-001",
        run_id="RUN-test",
        success=True,
        output="",
        error="",
        ack=None,
        return_code=0,
    )
    assert result.token_usage is None


# ---------------------------------------------------------------------------
# 7. onward show --runs display
# ---------------------------------------------------------------------------


def test_show_runs_flag_prints_run_table(tmp_path: Path, capsys: Any) -> None:
    """onward show TASK-001 --runs prints run history table."""
    _make_workspace(tmp_path)
    capsys.readouterr()
    from onward import cli

    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    assert cli.main(["show", "--root", str(tmp_path), "TASK-001", "--runs"]) == 0
    out = capsys.readouterr().out
    assert "Runs for TASK-001" in out
    assert "#1" in out


def test_show_runs_no_runs_yet(tmp_path: Path, capsys: Any) -> None:
    """onward show TASK-001 --runs prints 'No runs yet' when no runs exist."""
    from onward import cli

    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "P"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "T"]) == 0
    capsys.readouterr()

    assert cli.main(["show", "--root", str(tmp_path), "TASK-001", "--runs"]) == 0
    out = capsys.readouterr().out
    assert "No runs yet" in out


# ---------------------------------------------------------------------------
# 8. onward report --verbose run stats
# ---------------------------------------------------------------------------


def test_report_verbose_shows_run_stats(tmp_path: Path, capsys: Any) -> None:
    """onward report --verbose includes [Run stats] section."""
    _make_workspace(tmp_path)
    capsys.readouterr()
    from onward import cli

    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--root", str(tmp_path), "--verbose", "--no-color"]) == 0
    out = capsys.readouterr().out
    assert "[Run stats]" in out
    assert "Total runs:" in out
    assert "Pass rate:" in out


def test_report_without_verbose_has_no_run_stats(tmp_path: Path, capsys: Any) -> None:
    """onward report without --verbose does NOT include [Run stats]."""
    _make_workspace(tmp_path)
    capsys.readouterr()
    from onward import cli

    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--root", str(tmp_path), "--no-color"]) == 0
    out = capsys.readouterr().out
    assert "[Run stats]" not in out
