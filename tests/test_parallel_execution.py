"""Unit tests for DAG validation, parallel_execute, and work_max_parallel_tasks."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from onward.artifacts import Artifact
from onward.config import work_max_parallel_tasks, WorkspaceLayout
from onward.executor import Executor, ExecutorResult, TaskContext
from onward.execution import validate_chunk_dag, _is_model_error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(task_id: str, status: str = "open", depends_on: list[str] | None = None) -> Artifact:
    meta: dict = {
        "id": task_id,
        "type": "task",
        "status": status,
        "title": f"Task {task_id}",
    }
    if depends_on is not None:
        meta["depends_on"] = depends_on
    return Artifact(file_path=Path(f"/fake/{task_id}.md"), metadata=meta, body="")


# ---------------------------------------------------------------------------
# work_max_parallel_tasks
# ---------------------------------------------------------------------------


def test_max_parallel_tasks_default() -> None:
    assert work_max_parallel_tasks({}) == 1


def test_max_parallel_tasks_explicit() -> None:
    assert work_max_parallel_tasks({"work": {"max_parallel_tasks": 3}}) == 3


def test_max_parallel_tasks_clamped_to_one() -> None:
    assert work_max_parallel_tasks({"work": {"max_parallel_tasks": 0}}) == 1
    assert work_max_parallel_tasks({"work": {"max_parallel_tasks": -5}}) == 1


def test_max_parallel_tasks_invalid_string_falls_back() -> None:
    assert work_max_parallel_tasks({"work": {"max_parallel_tasks": "bad"}}) == 1


def test_max_parallel_tasks_none_falls_back() -> None:
    assert work_max_parallel_tasks({"work": {"max_parallel_tasks": None}}) == 1


def test_max_parallel_tasks_work_not_mapping() -> None:
    assert work_max_parallel_tasks({"work": None}) == 1


# ---------------------------------------------------------------------------
# validate_chunk_dag — valid graphs
# ---------------------------------------------------------------------------


def test_dag_empty_tasks_is_valid() -> None:
    assert validate_chunk_dag([]) == []


def test_dag_single_task_no_deps_is_valid() -> None:
    tasks = [_make_task("TASK-001")]
    assert validate_chunk_dag(tasks) == []


def test_dag_independent_tasks_no_deps_is_valid() -> None:
    tasks = [_make_task("TASK-001"), _make_task("TASK-002"), _make_task("TASK-003")]
    assert validate_chunk_dag(tasks) == []


def test_dag_linear_chain_is_valid() -> None:
    tasks = [
        _make_task("TASK-001"),
        _make_task("TASK-002", depends_on=["TASK-001"]),
        _make_task("TASK-003", depends_on=["TASK-002"]),
    ]
    assert validate_chunk_dag(tasks) == []


def test_dag_diamond_is_valid() -> None:
    tasks = [
        _make_task("TASK-001"),
        _make_task("TASK-002", depends_on=["TASK-001"]),
        _make_task("TASK-003", depends_on=["TASK-001"]),
        _make_task("TASK-004", depends_on=["TASK-002", "TASK-003"]),
    ]
    assert validate_chunk_dag(tasks) == []


def test_dag_dep_on_completed_external_task_is_valid() -> None:
    """A depends_on reference to a task outside the chunk is OK if that task is completed."""
    task = _make_task("TASK-002", depends_on=["TASK-001"])
    # With all_statuses provided, the external dep resolves as completed.
    errors = validate_chunk_dag([task], all_statuses={"TASK-001": "completed"})
    assert errors == []


def test_dag_dep_on_completed_external_task_via_task_list() -> None:
    """Passing the completed external task directly also suppresses the error."""
    task = _make_task("TASK-002", depends_on=["TASK-001"])
    external = _make_task("TASK-001", status="completed")
    errors = validate_chunk_dag([task, external])
    assert errors == []


def test_dag_dep_on_open_external_task_is_error() -> None:
    """External dep that is not completed is an error even with all_statuses."""
    task = _make_task("TASK-002", depends_on=["TASK-001"])
    errors = validate_chunk_dag([task], all_statuses={"TASK-001": "open"})
    assert any("TASK-001" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_chunk_dag — cycles
# ---------------------------------------------------------------------------


def test_dag_self_loop_is_cycle() -> None:
    tasks = [_make_task("TASK-001", depends_on=["TASK-001"])]
    errors = validate_chunk_dag(tasks)
    assert any("cycle" in e for e in errors)


def test_dag_two_node_cycle() -> None:
    tasks = [
        _make_task("TASK-001", depends_on=["TASK-002"]),
        _make_task("TASK-002", depends_on=["TASK-001"]),
    ]
    errors = validate_chunk_dag(tasks)
    assert any("cycle" in e for e in errors)


def test_dag_three_node_cycle() -> None:
    tasks = [
        _make_task("TASK-001", depends_on=["TASK-003"]),
        _make_task("TASK-002", depends_on=["TASK-001"]),
        _make_task("TASK-003", depends_on=["TASK-002"]),
    ]
    errors = validate_chunk_dag(tasks)
    assert any("cycle" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_chunk_dag — dangling refs
# ---------------------------------------------------------------------------


def test_dag_dangling_ref_to_open_external() -> None:
    """Dependency on non-existent (or non-completed) external task is an error."""
    tasks = [_make_task("TASK-002", depends_on=["TASK-GHOST"])]
    errors = validate_chunk_dag(tasks)
    assert any("TASK-GHOST" in e for e in errors)


# ---------------------------------------------------------------------------
# _is_model_error — model error detection
# ---------------------------------------------------------------------------


def _make_executor_result(
    success: bool = False, output: str = "", error: str = "", return_code: int = 1,
) -> ExecutorResult:
    return ExecutorResult(
        task_id="TASK-001", run_id="RUN-001", success=success,
        output=output, error=error, ack=None, return_code=return_code,
    )


def test_is_model_error_claude_cli_pattern() -> None:
    r = _make_executor_result(
        output="There's an issue with the selected model (sonnet-4.6). "
               "It may not exist or you may not have access to it."
    )
    assert _is_model_error(r, "executor exited with code 1") is True


def test_is_model_error_invalid_model_string() -> None:
    r = _make_executor_result(error="invalid model: foo-bar-baz")
    assert _is_model_error(r, "executor exited with code 1") is True


def test_is_model_error_unknown_model() -> None:
    r = _make_executor_result(error="unknown model identifier")
    assert _is_model_error(r, "") is True


def test_is_model_error_not_available() -> None:
    r = _make_executor_result(output="model xyz is not available for your account")
    assert _is_model_error(r, "") is True


def test_is_model_error_false_on_normal_failure() -> None:
    r = _make_executor_result(error="syntax error in generated code")
    assert _is_model_error(r, "executor exited with code 1") is False


def test_is_model_error_false_on_success() -> None:
    r = _make_executor_result(success=True, output="all good", return_code=0)
    assert _is_model_error(r, "") is False


def test_is_model_error_none_result() -> None:
    assert _is_model_error(None, "executor exited with code 1") is False


# ---------------------------------------------------------------------------
# parallel_execute — parallel dispatch
# ---------------------------------------------------------------------------


class _SuccessExecutor(Executor):
    """Executor that immediately succeeds; records call order and concurrency."""

    def __init__(self, *, delay: float = 0.0) -> None:
        self._delay = delay
        self.called: list[str] = []
        self._active = 0
        self._max_active = 0
        self._lock = threading.Lock()

    def execute_task(self, root: Path, ctx: TaskContext) -> ExecutorResult:
        tid = str(ctx.task.metadata.get("id", ""))
        with self._lock:
            self._active += 1
            self._max_active = max(self._max_active, self._active)
        if self._delay:
            time.sleep(self._delay)
        with self._lock:
            self._active -= 1
            self.called.append(tid)
        return ExecutorResult(
            task_id=tid,
            run_id=ctx.run_id,
            success=True,
            output="ok",
            error="",
            ack=None,
            return_code=0,
        )


class _FailingExecutor(Executor):
    """Executor that always fails."""

    def execute_task(self, root: Path, ctx: TaskContext) -> ExecutorResult:
        tid = str(ctx.task.metadata.get("id", ""))
        return ExecutorResult(
            task_id=tid,
            run_id=ctx.run_id,
            success=False,
            output="",
            error="simulated failure",
            ack=None,
            return_code=1,
        )


def _fake_config(root: Path, *, parallel: int = 2) -> dict:
    """Minimal config that disables hooks and sets max_parallel_tasks."""
    return {
        "work": {"max_parallel_tasks": parallel},
        "executor": {"enabled": True},
        "hooks": {},
    }


def _make_prepared_run(root: Path, task_id: str, config: dict):
    """Build a PreparedTaskRun for a fake task (no on-disk writes)."""
    from onward.execution import PreparedTaskRun
    from onward.util import now_iso, run_timestamp

    task = _make_task(task_id)
    run_id = f"RUN-{run_timestamp()}-{task_id}"
    run_json = root / f"{run_id}.json"
    run_log = root / f"{run_id}.log"
    run_json.write_text("{}", encoding="utf-8")
    run_log.write_text("", encoding="utf-8")

    ctx = TaskContext(
        task=task,
        model="test-model",
        run_id=run_id,
        plan_context=None,
        chunk_context=None,
        notes=None,
    )
    started_at = now_iso()
    run_record: dict = {
        "id": run_id,
        "type": "run",
        "target": task_id,
        "plan": None,
        "chunk": None,
        "status": "running",
        "model": "test-model",
        "executor": "test",
        "started_at": started_at,
        "finished_at": None,
        "log_path": str(run_log),
        "error": "",
    }
    output_log = root / f"{run_id}.output.log"
    return PreparedTaskRun(
        task=task,
        ctx=ctx,
        run_id=run_id,
        run_json=run_json,
        run_log=run_log,
        output_log=output_log,
        run_record=run_record,
        model="test-model",
        log_sections=["$ test"],
    )


def _mock_artifacts(monkeypatch, task_id: str) -> None:
    """Patch must_find_by_id and update_artifact_status to avoid real disk I/O."""
    from onward import execution as exec_mod

    def _fake_must_find(layout, tid, project=None):
        return _make_task(tid)

    def _fake_update_status(layout, artifact, status, project=None):
        pass

    def _fake_load_ongoing(layout, project=None):
        return {"version": 1, "updated_at": "2026-01-01T00:00:00Z", "active_runs": []}

    def _fake_write_ongoing(layout, payload, project=None):
        pass

    monkeypatch.setattr(exec_mod, "must_find_by_id", _fake_must_find)
    monkeypatch.setattr(exec_mod, "update_artifact_status", _fake_update_status)
    monkeypatch.setattr(exec_mod, "load_ongoing", _fake_load_ongoing)
    monkeypatch.setattr(exec_mod, "_write_ongoing", _fake_write_ongoing)


def test_parallel_execute_all_succeed(tmp_path: Path, monkeypatch) -> None:
    from onward.execution import parallel_execute

    config = _fake_config(tmp_path, parallel=2)
    executor = _SuccessExecutor()
    tasks = ["TASK-001", "TASK-002", "TASK-003"]
    prepared = [_make_prepared_run(tmp_path, tid, config) for tid in tasks]

    for tid in tasks:
        _mock_artifacts(monkeypatch, tid)

    ok, outcomes = parallel_execute(WorkspaceLayout.from_config(tmp_path, {}), config, executor, prepared, max_workers=2)
    assert ok is True
    assert len(outcomes) == 3
    assert all(task_ok for _, task_ok in outcomes)


def test_parallel_execute_failure_propagates(tmp_path: Path, monkeypatch) -> None:
    from onward.execution import parallel_execute

    config = _fake_config(tmp_path, parallel=2)
    executor = _FailingExecutor()
    tasks = ["TASK-001", "TASK-002"]
    prepared = [_make_prepared_run(tmp_path, tid, config) for tid in tasks]

    for tid in tasks:
        _mock_artifacts(monkeypatch, tid)

    ok, outcomes = parallel_execute(WorkspaceLayout.from_config(tmp_path, {}), config, executor, prepared, max_workers=2)
    assert ok is False
    assert any(not task_ok for _, task_ok in outcomes)


def test_parallel_execute_concurrency(tmp_path: Path, monkeypatch) -> None:
    """With max_workers=3 and a delay, tasks should run concurrently."""
    from onward.execution import parallel_execute

    config = _fake_config(tmp_path, parallel=3)
    executor = _SuccessExecutor(delay=0.05)
    tasks = ["TASK-001", "TASK-002", "TASK-003"]
    prepared = [_make_prepared_run(tmp_path, tid, config) for tid in tasks]

    for tid in tasks:
        _mock_artifacts(monkeypatch, tid)

    ok, outcomes = parallel_execute(WorkspaceLayout.from_config(tmp_path, {}), config, executor, prepared, max_workers=3)
    assert ok is True
    # With a delay and 3 workers, max concurrent should be > 1
    assert executor._max_active > 1


def test_parallel_execute_serial_max_workers_1(tmp_path: Path, monkeypatch) -> None:
    """max_workers=1 runs serially; max concurrent is always 1."""
    from onward.execution import parallel_execute

    config = _fake_config(tmp_path, parallel=1)
    executor = _SuccessExecutor(delay=0.02)
    tasks = ["TASK-001", "TASK-002"]
    prepared = [_make_prepared_run(tmp_path, tid, config) for tid in tasks]

    for tid in tasks:
        _mock_artifacts(monkeypatch, tid)

    ok, outcomes = parallel_execute(WorkspaceLayout.from_config(tmp_path, {}), config, executor, prepared, max_workers=1)
    assert ok is True
    assert executor._max_active == 1
