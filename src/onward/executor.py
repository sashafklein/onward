"""Executor protocol for Onward task runs.

Onward delegates each task (or batch of tasks) to an :class:`Executor` implementation.
:class:`BuiltinExecutor` (in :mod:`onward.executor_builtin`) talks to Claude/Cursor CLIs directly;
:class:`SubprocessExecutor` adapts external commands that consume the JSON stdin protocol.

Callers build a :class:`TaskContext` per task (resolved model, run id, artifact, optional
plan/chunk context and notes). Implementations return :class:`ExecutorResult` with
captured streams, exit status, and an optional parsed task-result ack dict.
"""

from __future__ import annotations

import json
import os
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onward.artifacts import Artifact
from onward.executor_ack import find_task_success_ack
from onward.executor_payload import with_schema_version


@dataclass(frozen=True)
class TaskContext:
    """Inputs for a single executor invocation."""

    task: Artifact
    model: str
    run_id: str
    plan_context: dict[str, Any] | None
    chunk_context: dict[str, Any] | None
    notes: str | None


@dataclass
class ExecutorResult:
    """Outcome of one executor run for a task."""

    task_id: str
    run_id: str
    success: bool
    output: str
    error: str
    ack: dict[str, Any] | None
    return_code: int


class Executor(ABC):
    """Abstract executor: one task or a sequential batch."""

    @abstractmethod
    def execute_task(self, root: Path, ctx: TaskContext) -> ExecutorResult:
        """Run a single task in the workspace rooted at ``root``."""

    def execute_batch(self, root: Path, tasks: list[TaskContext]) -> Iterator[ExecutorResult]:
        """Run ``tasks`` in order; default implementation calls :meth:`execute_task` per item."""
        for ctx in tasks:
            yield self.execute_task(root, ctx)


def build_subprocess_task_payload(ctx: TaskContext) -> dict[str, Any]:
    """Build the ``type: task`` stdin payload for external executors.

    Matches the JSON object passed to the executor in ``execution._execute_task_run``
    (before ``schema_version`` is applied via :func:`onward.executor_payload.with_schema_version`).
    """
    task_id = str(ctx.task.metadata.get("id", ""))
    notes_raw = ctx.notes if ctx.notes is not None else ""
    notes_value = notes_raw.strip() if notes_raw.strip() else None
    return {
        "type": "task",
        "run_id": ctx.run_id,
        "task": ctx.task.metadata,
        "body": ctx.task.body,
        "notes": notes_value,
        "notes_hint": (
            f"To add a note to this task, run: onward note {task_id} \"your note\". "
            f"To read existing notes: onward note {task_id}"
        ),
        "chunk": ctx.chunk_context,
        "plan": ctx.plan_context,
    }


class SubprocessExecutor(Executor):
    """Run tasks by spawning ``[command, *args]`` with JSON on stdin (legacy protocol)."""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        *,
        require_success_ack: bool = False,
    ) -> None:
        self._command = command
        self._args = list(args) if args else []
        self._require_success_ack = require_success_ack

    def execute_task(self, root: Path, ctx: TaskContext) -> ExecutorResult:
        task_id = str(ctx.task.metadata.get("id", ""))
        run_id = ctx.run_id
        cmd = [self._command, *[str(a) for a in self._args]]
        payload = with_schema_version(build_subprocess_task_payload(ctx))
        json_input = json.dumps(payload, indent=2, ensure_ascii=False)
        child_env = {**os.environ, "ONWARD_RUN_ID": run_id}

        try:
            result = subprocess.run(
                cmd,
                cwd=root,
                input=json_input,
                text=True,
                capture_output=True,
                check=False,
                env=child_env,
            )
        except FileNotFoundError:
            return ExecutorResult(
                task_id=task_id,
                run_id=run_id,
                success=False,
                output="",
                error=f"executor command not found: {self._command}",
                ack=None,
                return_code=-1,
            )
        except Exception as exc:  # noqa: BLE001
            return ExecutorResult(
                task_id=task_id,
                run_id=run_id,
                success=False,
                output="",
                error=str(exc),
                ack=None,
                return_code=-1,
            )

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        output = stdout.rstrip()
        if stderr.strip():
            stderr_block = stderr.rstrip()
            output = f"{output}\n\n[task stderr]\n{stderr_block}" if output else f"[task stderr]\n{stderr_block}"

        ok = result.returncode == 0
        error = ""
        ack_obj: dict[str, Any] | None = None

        if ok:
            found, ack_err, ack_obj = find_task_success_ack(stdout, stderr, run_id)
            if self._require_success_ack and not found:
                ok = False
                error = ack_err
        else:
            error = f"executor exited with code {result.returncode}"

        return ExecutorResult(
            task_id=task_id,
            run_id=run_id,
            success=ok,
            output=output,
            error=error,
            ack=ack_obj,
            return_code=result.returncode,
        )


from onward.executor_builtin import BuiltinExecutor  # noqa: E402 — re-export; defined after ABC to break cycles
