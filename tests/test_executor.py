"""Executor protocol, :class:`~onward.executor.SubprocessExecutor`, and batch wave behavior."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from onward import cli
from onward.artifacts import Artifact
from onward.config import resolve_executor
from onward.executor import (
    Executor,
    ExecutorResult,
    SubprocessExecutor,
    TaskContext,
    build_subprocess_task_payload,
)
from onward.executor_ack import SUCCESS_ACK_SCHEMA_VERSION
from onward.executor_payload import validate_executor_stdin_payload, with_schema_version
from onward.execution import _run_hooked_executor_batch

from tests.workspace_helpers import (
    clear_post_chunk_markdown,
    clear_post_task_markdown,
    clear_post_task_shell,
)


def _set_builtin_executor(root: Path) -> None:
    """Avoid preflight failure when ``onward-exec`` is not on PATH in CI sandboxes."""
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    config_path.write_text(raw.replace("  command: onward-exec", '  command: builtin'), encoding="utf-8")


def test_executor_import_surface() -> None:
    from onward.executor import Executor as E
    from onward.executor import ExecutorResult as ER
    from onward.executor import TaskContext as TC

    assert E is Executor
    assert ER is ExecutorResult
    assert TC is TaskContext


def test_executor_abc_cannot_instantiate() -> None:
    with pytest.raises(TypeError, match="abstract"):
        Executor()  # type: ignore[misc]


def test_execute_batch_default_yields_in_order(tmp_path: Path) -> None:
    class RecordingExecutor(Executor):
        def execute_task(self, root: Path, ctx: TaskContext) -> ExecutorResult:
            tid = str(ctx.task.metadata.get("id", ""))
            return ExecutorResult(
                task_id=tid,
                run_id=ctx.run_id,
                success=True,
                output=tid,
                error="",
                ack=None,
                return_code=0,
            )

    ex = RecordingExecutor()
    tasks = [
        TaskContext(
            task=Artifact(tmp_path / "a.md", "", {"id": "TASK-001"}),
            model="m",
            run_id="r1",
            plan_context=None,
            chunk_context=None,
            notes=None,
        ),
        TaskContext(
            task=Artifact(tmp_path / "b.md", "", {"id": "TASK-002"}),
            model="m",
            run_id="r2",
            plan_context=None,
            chunk_context=None,
            notes=None,
        ),
    ]
    results = list(ex.execute_batch(tmp_path, tasks))
    assert [r.task_id for r in results] == ["TASK-001", "TASK-002"]
    assert [r.run_id for r in results] == ["r1", "r2"]


def test_resolve_executor_subprocess_when_command_set() -> None:
    ex = resolve_executor({"executor": {"command": "onward-exec", "args": []}})
    assert isinstance(ex, SubprocessExecutor)


def test_resolve_executor_builtin_when_command_absent() -> None:
    from onward.executor import BuiltinExecutor

    ex = resolve_executor({})
    assert isinstance(ex, BuiltinExecutor)


def test_resolve_executor_builtin_when_command_is_builtin_literal() -> None:
    from onward.executor import BuiltinExecutor

    ex = resolve_executor({"executor": {"command": "builtin"}})
    assert isinstance(ex, BuiltinExecutor)


def test_resolve_executor_builtin_when_command_empty_string() -> None:
    from onward.executor import BuiltinExecutor

    ex = resolve_executor({"executor": {"command": ""}})
    assert isinstance(ex, BuiltinExecutor)


def test_resolve_executor_builtin_command_case_insensitive() -> None:
    from onward.executor import BuiltinExecutor

    ex = resolve_executor({"executor": {"command": "Builtin"}})
    assert isinstance(ex, BuiltinExecutor)


def test_resolve_executor_passes_require_success_ack_to_subprocess() -> None:
    ex = resolve_executor(
        {"executor": {"command": "x"}, "work": {"require_success_ack": True}},
    )
    assert isinstance(ex, SubprocessExecutor)
    assert ex._require_success_ack is True  # noqa: SLF001


def _subprocess_ctx(
    tmp_path: Path,
    *,
    task_id: str = "TASK-001",
    run_id: str = "RUN-1-TASK-001",
    notes: str | None = None,
    chunk: dict | None = None,
    plan: dict | None = None,
) -> TaskContext:
    return TaskContext(
        task=Artifact(
            tmp_path / f"{task_id}.md",
            "task body",
            {"id": task_id, "title": "T", "chunk": "CHUNK-1", "plan": "PLAN-1"},
        ),
        model="opus-latest",
        run_id=run_id,
        plan_context=plan,
        chunk_context=chunk,
        notes=notes,
    )


@patch("onward.executor.subprocess.run")
def test_subprocess_executor_payload_matches_execution_shape(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    chunk_ctx = {"metadata": {"id": "CHUNK-1"}, "body": "c"}
    plan_ctx = {"metadata": {"id": "PLAN-1"}, "body": "p"}
    ctx = _subprocess_ctx(tmp_path, chunk=chunk_ctx, plan=plan_ctx, notes="  hello  ")

    ex = SubprocessExecutor("onward-exec", ["--foo"])
    ex.execute_task(tmp_path, ctx)

    mock_run.assert_called_once()
    call_kw = mock_run.call_args.kwargs
    assert call_kw["cwd"] == tmp_path
    assert call_kw["text"] is True
    assert call_kw["capture_output"] is True
    assert call_kw["check"] is False

    parsed = json.loads(call_kw["input"])
    expected = with_schema_version(build_subprocess_task_payload(ctx))
    assert parsed == expected
    assert validate_executor_stdin_payload(parsed) == []


@patch("onward.executor.subprocess.run")
def test_subprocess_executor_notes_none_becomes_null_in_json(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    ctx = _subprocess_ctx(tmp_path, notes=None)
    SubprocessExecutor("x").execute_task(tmp_path, ctx)
    parsed = json.loads(mock_run.call_args.kwargs["input"])
    assert parsed["notes"] is None


@patch("onward.executor.subprocess.run")
def test_subprocess_executor_sets_onward_run_id_env(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    ctx = _subprocess_ctx(tmp_path, run_id="RUN-xyz-TASK-001")
    SubprocessExecutor("x").execute_task(tmp_path, ctx)
    env = mock_run.call_args.kwargs["env"]
    assert env["ONWARD_RUN_ID"] == "RUN-xyz-TASK-001"


@patch("onward.executor.subprocess.run")
def test_subprocess_executor_success_without_ack_when_not_required(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="done\n", stderr="")
    ctx = _subprocess_ctx(tmp_path)
    r = SubprocessExecutor("x", require_success_ack=False).execute_task(tmp_path, ctx)
    assert r.success
    assert r.return_code == 0
    assert r.ack is None
    assert r.error == ""


@patch("onward.executor.subprocess.run")
def test_subprocess_executor_parses_ack(mock_run: MagicMock, tmp_path: Path) -> None:
    line = json.dumps(
        {
            "onward_task_result": {
                "status": "completed",
                "schema_version": SUCCESS_ACK_SCHEMA_VERSION,
                "run_id": "RUN-1-TASK-001",
            }
        }
    )
    mock_run.return_value = MagicMock(returncode=0, stdout=f"ok\n{line}\n", stderr="")
    ctx = _subprocess_ctx(tmp_path)
    r = SubprocessExecutor("x").execute_task(tmp_path, ctx)
    assert r.success
    assert r.ack is not None
    assert r.ack["onward_task_result"]["status"] == "completed"


@patch("onward.executor.subprocess.run")
def test_subprocess_executor_require_ack_fails_without_line(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="no json ack here\n", stderr="")
    ctx = _subprocess_ctx(tmp_path)
    r = SubprocessExecutor("x", require_success_ack=True).execute_task(tmp_path, ctx)
    assert not r.success
    assert r.return_code == 0
    assert "onward_task_result" in r.error


@patch("onward.executor.subprocess.run")
def test_subprocess_executor_nonzero_exit(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="boom")
    ctx = _subprocess_ctx(tmp_path)
    r = SubprocessExecutor("x").execute_task(tmp_path, ctx)
    assert not r.success
    assert r.return_code == 2
    assert "code 2" in r.error
    assert r.ack is None


@patch("onward.executor.subprocess.run")
def test_subprocess_executor_file_not_found(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.side_effect = FileNotFoundError()
    ctx = _subprocess_ctx(tmp_path)
    r = SubprocessExecutor("missing-binary-xyz").execute_task(tmp_path, ctx)
    assert not r.success
    assert r.return_code == -1
    assert "not found" in r.error
    assert "missing-binary-xyz" in r.error


@patch("onward.executor.subprocess.run")
def test_subprocess_execute_batch_sequential(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    ex = SubprocessExecutor("cmd")
    tasks = [
        _subprocess_ctx(tmp_path, task_id="TASK-A", run_id="RUN-a"),
        _subprocess_ctx(tmp_path, task_id="TASK-B", run_id="RUN-b"),
    ]
    results = list(ex.execute_batch(tmp_path, tasks))
    assert len(results) == 2
    assert [r.task_id for r in results] == ["TASK-A", "TASK-B"]
    assert mock_run.call_count == 2


def test_subprocess_execute_batch_empty_yields_nothing(tmp_path: Path) -> None:
    with patch("onward.executor.subprocess.run") as mock_run:
        mock_run.side_effect = AssertionError("execute_batch with no tasks must not spawn")
        assert list(SubprocessExecutor("cmd").execute_batch(tmp_path, [])) == []


def test_run_hooked_executor_batch_empty_prepared_is_noop(tmp_path: Path) -> None:
    class _NeverRun(Executor):
        def execute_task(self, root: Path, ctx: TaskContext) -> ExecutorResult:
            raise AssertionError("no tasks")

    ok, outcomes = _run_hooked_executor_batch(tmp_path, {}, _NeverRun(), [])
    assert ok is True
    assert outcomes == []


class _FailOnSecondTaskExecutor(Executor):
    """First task succeeds; second fails; further tasks would not be consumed by the wave loop."""

    def __init__(self) -> None:
        self.seen_ids: list[str] = []

    def execute_task(self, root: Path, ctx: TaskContext) -> ExecutorResult:
        tid = str(ctx.task.metadata.get("id", ""))
        first = len(self.seen_ids) == 0
        self.seen_ids.append(tid)
        ok = first
        return ExecutorResult(
            task_id=tid,
            run_id=ctx.run_id,
            success=ok,
            output="out",
            error="" if ok else "boom",
            ack=None,
            return_code=0 if ok else 1,
        )


class _AllOkExecutor(Executor):
    def __init__(self) -> None:
        self.seen_ids: list[str] = []

    def execute_task(self, root: Path, ctx: TaskContext) -> ExecutorResult:
        tid = str(ctx.task.metadata.get("id", ""))
        self.seen_ids.append(tid)
        return ExecutorResult(
            task_id=tid,
            run_id=ctx.run_id,
            success=True,
            output="ok",
            error="",
            ack=None,
            return_code=0,
        )


def test_work_chunk_three_tasks_all_succeed_in_one_wave(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ex = _AllOkExecutor()
    monkeypatch.setattr("onward.execution.resolve_executor", lambda _cfg: ex)

    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    _set_builtin_executor(tmp_path)
    clear_post_task_shell(tmp_path)
    clear_post_task_markdown(tmp_path)
    clear_post_chunk_markdown(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "P"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    for title in ("A", "B", "C"):
        assert (
            cli.main(
                [
                    "new",
                    "--root",
                    str(tmp_path),
                    "task",
                    "CHUNK-001",
                    title,
                    "--description",
                    "d",
                ]
            )
            == 0
        )
    capsys.readouterr()
    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    assert code == 0
    assert set(ex.seen_ids) == {"TASK-001", "TASK-002", "TASK-003"}


def test_work_chunk_stops_wave_after_second_task_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ex = _FailOnSecondTaskExecutor()
    monkeypatch.setattr("onward.execution.resolve_executor", lambda _cfg: ex)

    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    _set_builtin_executor(tmp_path)
    clear_post_task_shell(tmp_path)
    clear_post_task_markdown(tmp_path)
    clear_post_chunk_markdown(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "P"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    for title in ("A", "B", "C"):
        assert (
            cli.main(
                [
                    "new",
                    "--root",
                    str(tmp_path),
                    "task",
                    "CHUNK-001",
                    title,
                    "--description",
                    "d",
                ]
            )
            == 0
        )
    capsys.readouterr()
    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    assert code == 1
    assert len(ex.seen_ids) == 2
    assert "Stopping chunk work" in capsys.readouterr().out
