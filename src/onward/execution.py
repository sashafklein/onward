from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onward.artifacts import (
    Artifact,
    collect_artifacts,
    find_by_id,
    must_find_by_id,
    read_notes,
    regenerate_indexes,
    update_artifact_status,
    write_artifact,
)
from onward.config import (
    is_executor_enabled,
    load_workspace_config,
    model_setting,
    resolve_executor,
    resolve_model_for_task,
    work_max_retries,
    work_sequential_by_default,
)
from onward.executor import Executor, ExecutorResult, TaskContext
from onward.executor_ack import parse_task_result
from onward.preflight import preflight_executor_command, preflight_shell_invocation
from onward.executor_payload import with_schema_version
from onward.util import (
    as_str_list,
    clean_string,
    dump_run_json_record,
    dump_simple_yaml,
    now_iso,
    read_run_json_record,
    run_timestamp,
)


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


def _hook_commands(config: dict[str, Any], key: str) -> list[str]:
    hooks = config.get("hooks", {})
    if not isinstance(hooks, dict):
        return []
    value = hooks.get(key)
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    scalar = str(value or "").strip()
    return [scalar] if scalar else []


def _hook_markdown_path(config: dict[str, Any], key: str) -> str:
    hooks = config.get("hooks", {})
    if not isinstance(hooks, dict):
        return ""
    value = hooks.get(key)
    return str(value or "").strip()


def _run_shell_hooks(
    root: Path,
    commands: list[str],
    phase: str,
    extra_env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    if not commands:
        return True, f"[{phase}]\n(no hooks)"

    child_env = {**os.environ, **extra_env} if extra_env else None

    lines = [f"[{phase}]"]
    for i, command in enumerate(commands, start=1):
        lines.append(f"$ {command}")
        try:
            result = subprocess.run(
                command,
                cwd=root,
                shell=True,
                text=True,
                capture_output=True,
                check=False,
                env=child_env,
            )
        except Exception as exc:  # noqa: BLE001
            lines.append(f"[error] {exc}")
            return False, "\n".join(lines)
        if result.stdout:
            lines.append("[stdout]")
            lines.append(result.stdout.rstrip())
        if result.stderr:
            lines.append("[stderr]")
            lines.append(result.stderr.rstrip())
        if result.returncode != 0:
            lines.append(f"[error] exit code {result.returncode}")
            return False, "\n".join(lines)
    return True, "\n".join(lines)


def _stdin_json_executor_argv(config: dict[str, Any]) -> list[str]:
    """Argv for markdown / JSON-stdin hooks.

    Task runs may use :class:`~onward.executor.BuiltinExecutor`, which does not accept the
    stdin JSON protocol. Hooks still use the legacy subprocess shape; when the workspace
    executor is built-in, fall back to ``onward-exec`` (reference adapter).
    """
    block = config.get("executor", {})
    if not isinstance(block, dict):
        block = {}
    command = clean_string(block.get("command")) or "onward-exec"
    if command.lower() == "builtin":
        command = "onward-exec"
    args = block.get("args", [])
    if not isinstance(args, list):
        args = []
    return [command, *[str(item) for item in args]]


def _executor_log_line(config: dict[str, Any]) -> str:
    """First log line describing how the task executor was selected (not necessarily argv)."""
    block = config.get("executor", {})
    if not isinstance(block, dict):
        block = {}
    command = clean_string(block.get("command"))
    if not command or command.lower() == "builtin":
        return "$ builtin"
    args = block.get("args", [])
    if not isinstance(args, list):
        args = []
    return "$ " + " ".join([command, *[str(a) for a in args]])


def _run_markdown_hook(
    root: Path,
    cmd: list[str],
    hook_rel_path: str,
    phase: str,
    model: str,
    task: Artifact,
    run_id: str,
) -> tuple[bool, str]:
    if not hook_rel_path:
        return True, f"[{phase}]\n(no hook)"

    hook_path = root / hook_rel_path
    if not hook_path.exists():
        return False, f"[{phase}]\n[error] hook file not found: {hook_rel_path}"

    payload = {
        "type": "hook",
        "phase": phase,
        "run_id": run_id,
        "model": model,
        "hook_path": hook_rel_path,
        "hook_body": hook_path.read_text(encoding="utf-8"),
        "task": task.metadata,
        "task_body": task.body,
    }

    lines = [f"[{phase}]", f"$ {' '.join(cmd)}"]
    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            input=json.dumps(with_schema_version(payload), indent=2, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        lines.append(f"[error] {exc}")
        return False, "\n".join(lines)

    if result.stdout:
        lines.append("[stdout]")
        lines.append(result.stdout.rstrip())
    if result.stderr:
        lines.append("[stderr]")
        lines.append(result.stderr.rstrip())
    if result.returncode != 0:
        lines.append(f"[error] exit code {result.returncode}")
        return False, "\n".join(lines)
    return True, "\n".join(lines)


# ---------------------------------------------------------------------------
# Ongoing runs
# ---------------------------------------------------------------------------


def load_ongoing(root: Path) -> dict[str, Any]:
    path = root / ".onward/ongoing.json"
    if not path.exists():
        return {"version": 1, "updated_at": now_iso(), "active_runs": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = {"version": 1, "updated_at": now_iso(), "active_runs": []}
    if not isinstance(payload, dict):
        payload = {"version": 1, "updated_at": now_iso(), "active_runs": []}
    if not isinstance(payload.get("active_runs"), list):
        payload["active_runs"] = []
    return payload


def _write_ongoing(root: Path, payload: dict[str, Any]) -> None:
    payload["updated_at"] = now_iso()
    path = root / ".onward/ongoing.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _register_active_run(
    root: Path,
    run_id: str,
    task_id: str,
    model: str,
    run_log: Path,
    started_at: str,
) -> None:
    """Append one entry to ``ongoing.json`` immediately before the executor runs for that task."""
    ongoing = load_ongoing(root)
    active_runs = list(ongoing.get("active_runs", []))
    active_runs.append(
        {
            "id": run_id,
            "target": task_id,
            "status": "running",
            "model": model,
            "log_path": str(run_log.relative_to(root)),
            "started_at": started_at,
        }
    )
    ongoing["active_runs"] = active_runs
    _write_ongoing(root, ongoing)


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------


class CircuitBreakerError(ValueError):
    """Task has reached ``work.max_retries``; ``onward work`` skips until ``onward retry`` or config change."""


@dataclass
class PreparedTaskRun:
    """One task run after ``run_count`` bump and run JSON scaffolding; ready for hook + executor steps."""

    task: Artifact
    ctx: TaskContext
    run_id: str
    run_json: Path
    run_log: Path
    run_record: dict[str, Any]
    model: str
    log_sections: list[str]


def _prepare_task_run(root: Path, task: Artifact, config: dict[str, Any]) -> PreparedTaskRun:
    task_id = str(task.metadata.get("id", ""))
    fresh = must_find_by_id(root, task_id)
    run_count = int(fresh.metadata.get("run_count", 0)) + 1
    fresh.metadata["run_count"] = run_count
    fresh.metadata["updated_at"] = now_iso()
    write_artifact(fresh)
    regenerate_indexes(root)
    task = must_find_by_id(root, task_id)

    model = resolve_model_for_task(config, task.metadata)

    block = config.get("executor", {})
    if not isinstance(block, dict):
        block = {}
    exec_cmd = clean_string(block.get("command"))
    executor_record = "builtin" if (not exec_cmd or exec_cmd.lower() == "builtin") else exec_cmd

    run_id = f"RUN-{run_timestamp()}-{task_id}"
    run_dir = root / ".onward/runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / f"{run_id}.json"
    run_log = run_dir / f"{run_id}.log"

    started_at = now_iso()
    run_record: dict[str, Any] = {
        "id": run_id,
        "type": "run",
        "target": task_id,
        "plan": task.metadata.get("plan"),
        "chunk": task.metadata.get("chunk"),
        "status": "running",
        "model": model,
        "executor": executor_record,
        "started_at": started_at,
        "finished_at": None,
        "log_path": str(run_log.relative_to(root)),
        "error": "",
    }
    run_json.write_text(dump_run_json_record(run_record), encoding="utf-8")

    notes = read_notes(root, task_id)
    chunk_context: dict[str, Any] | None = None
    plan_context: dict[str, Any] | None = None
    chunk_id = clean_string(task.metadata.get("chunk"))
    plan_id = clean_string(task.metadata.get("plan"))
    if chunk_id:
        chunk_art = find_by_id(root, chunk_id)
        if chunk_art:
            chunk_context = {"metadata": chunk_art.metadata, "body": chunk_art.body}
    if plan_id:
        plan_art = find_by_id(root, plan_id)
        if plan_art:
            plan_context = {"metadata": plan_art.metadata, "body": plan_art.body}

    ctx = TaskContext(
        task=task,
        model=model,
        run_id=run_id,
        plan_context=plan_context,
        chunk_context=chunk_context,
        notes=notes if notes.strip() else None,
    )
    log_sections: list[str] = [_executor_log_line(config)]
    return PreparedTaskRun(
        task=task,
        ctx=ctx,
        run_id=run_id,
        run_json=run_json,
        run_log=run_log,
        run_record=run_record,
        model=model,
        log_sections=log_sections,
    )


def _run_hooked_executor_batch(
    root: Path,
    config: dict[str, Any],
    executor: Executor,
    prepared_list: list[PreparedTaskRun],
) -> tuple[bool, list[tuple[str, bool]]]:
    """Pre/post hooks per task; one :meth:`~onward.executor.Executor.execute_batch` iterator for executor steps.

    For each task: run ``pre_task_shell``, then consume one step from ``execute_batch`` (which runs
    the executor for that task), then post hooks on success. Stops the wave on first failure.
    If ``pre_task_shell`` fails (or executor is disabled), that task is finalized as failed without
    advancing the batch iterator, so later tasks are not executed.
    """
    hook_cmd = _stdin_json_executor_argv(config)
    pre_shell = _hook_commands(config, "pre_task_shell")
    post_shell = _hook_commands(config, "post_task_shell")
    post_md = _hook_markdown_path(config, "post_task_markdown")

    contexts = [p.ctx for p in prepared_list]
    batch_iter = executor.execute_batch(root, contexts)
    outcomes: list[tuple[str, bool]] = []
    wave_ok = True

    for p in prepared_list:
        task = p.task
        task_id = str(task.metadata.get("id", ""))
        run_id = p.run_id
        model = p.model
        run_record = p.run_record
        run_json = p.run_json
        run_log = p.run_log
        log_sections = p.log_sections

        hook_env = {
            "ONWARD_RUN_ID": run_id,
            "ONWARD_TASK_ID": task_id,
            "ONWARD_TASK_TITLE": str(task.metadata.get("title", "")),
        }

        pre_shell_ok, pre_shell_log = _run_shell_hooks(root, pre_shell, "pre_task_shell", hook_env)
        log_sections.append(pre_shell_log)
        error = ""
        ok = False
        ack_obj: dict[str, Any] | None = None
        ex_result: ExecutorResult | None = None

        if not pre_shell_ok:
            error = "pre_task_shell hook failed"
        elif not is_executor_enabled(config):
            error = "executor.enabled is false in .onward.config.yaml (executor disabled)"
        else:
            _register_active_run(
                root,
                run_id,
                task_id,
                model,
                run_log,
                str(run_record["started_at"]),
            )
            try:
                ex_result = next(batch_iter)
            except StopIteration:
                error = "executor batch ended early"
            else:
                if ex_result.task_id != task_id:
                    error = f"executor result task_id mismatch ({ex_result.task_id!r} != {task_id!r})"
                elif ex_result.run_id != run_id:
                    error = f"executor result run_id mismatch ({ex_result.run_id!r} != {run_id!r})"
                else:
                    if ex_result.output.strip():
                        log_sections.append(ex_result.output.rstrip())
                    ok = ex_result.success
                    if not ok:
                        error = ex_result.error or f"executor exited with code {ex_result.return_code}"
                    ack_obj = ex_result.ack

        if ok and not error:
            post_shell_ok, post_shell_log = _run_shell_hooks(root, post_shell, "post_task_shell", hook_env)
            log_sections.append(post_shell_log)
            if not post_shell_ok:
                ok = False
                error = "post_task_shell hook failed"
        if ok and not error:
            post_md_ok, post_md_log = _run_markdown_hook(
                root, hook_cmd, post_md, "post_task_markdown", model, task, run_id
            )
            log_sections.append(post_md_log)
            if not post_md_ok:
                ok = False
                error = "post_task_markdown hook failed"

        if error:
            log_sections.append(f"[error] {error}")
        run_log.write_text(
            "\n\n".join(section.rstrip() for section in log_sections if section).rstrip() + "\n",
            encoding="utf-8",
        )

        finished_at = now_iso()
        run_record["status"] = "completed" if ok else "failed"
        run_record["finished_at"] = finished_at
        run_record["error"] = error
        if ack_obj is not None:
            run_record["success_ack"] = ack_obj
            run_record["task_result"] = parse_task_result(ack_obj)
        run_json.write_text(dump_run_json_record(run_record), encoding="utf-8")

        ongoing = load_ongoing(root)
        remaining = [
            item
            for item in ongoing.get("active_runs", [])
            if str(item.get("id", "")) != run_id
        ]
        ongoing["active_runs"] = remaining
        _write_ongoing(root, ongoing)

        refreshed = must_find_by_id(root, task_id)
        refreshed.metadata["last_run_status"] = "completed" if ok else "failed"
        update_artifact_status(root, refreshed, "completed" if ok else "failed")

        outcomes.append((run_id, ok))
        if not ok:
            wave_ok = False
            break

    return wave_ok, outcomes


def _execute_task_run(root: Path, task: Artifact) -> tuple[bool, str]:
    task_id = str(task.metadata.get("id", ""))
    config = load_workspace_config(root)
    executor = resolve_executor(config)
    prepared = _prepare_task_run(root, must_find_by_id(root, task_id), config)
    ok, _ = _run_hooked_executor_batch(root, config, executor, [prepared])
    return ok, prepared.run_id


def work_task(root: Path, task: Artifact) -> tuple[bool, str]:
    if str(task.metadata.get("type", "")) != "task":
        raise ValueError(f"{task.metadata.get('id')} is not a task")

    config = load_workspace_config(root)
    preflight_err = preflight_executor_command(config)
    if preflight_err:
        raise ValueError(preflight_err)

    tid = str(task.metadata.get("id", ""))
    fresh = must_find_by_id(root, tid)
    current = str(fresh.metadata.get("status", ""))
    if current == "completed":
        return True, ""
    if current not in {"open", "in_progress"}:
        if current == "canceled":
            raise ValueError(
                "cannot work task in state 'canceled' "
                "(only open or in_progress tasks can run; edit status or add a follow-up task). "
                "See docs/LIFECYCLE.md"
            )
        if current == "failed":
            raise ValueError(
                "cannot work task in state 'failed' "
                "(run onward retry TASK-* to reset to open, then onward work again). "
                "See docs/LIFECYCLE.md"
            )
        raise ValueError(
            f"cannot work task in state {current!r} "
            f"(expected open or in_progress). See docs/LIFECYCLE.md"
        )

    run_count = int(fresh.metadata.get("run_count", 0))
    max_r = work_max_retries(config)
    if max_r > 0 and run_count >= max_r:
        raise CircuitBreakerError(
            f"{tid} has reached run_count={run_count} (work.max_retries={max_r}); "
            f"use 'onward retry {tid}' to reset run_count, or set work.max_retries: 0 for unlimited. "
            "See docs/LIFECYCLE.md"
        )

    update_artifact_status(root, fresh, "in_progress")
    return _execute_task_run(root, fresh)


def ordered_ready_chunk_tasks(root: Path, chunk_id: str) -> tuple[list[Artifact], bool]:
    artifacts = collect_artifacts(root)
    tasks = [
        a
        for a in artifacts
        if str(a.metadata.get("type", "")) == "task"
        and str(a.metadata.get("chunk", "")) == chunk_id
        and str(a.metadata.get("status", "")) in {"open", "in_progress"}
    ]
    tasks.sort(key=lambda a: str(a.metadata.get("id", "")))
    if not tasks:
        return [], True

    status_by_id = {
        str(a.metadata.get("id", "")): str(a.metadata.get("status", ""))
        for a in artifacts
    }
    ready: list[Artifact] = []
    blocked_exists = False
    for task in tasks:
        deps = as_str_list(task.metadata.get("depends_on")) + as_str_list(
            task.metadata.get("blocked_by")
        )
        unmet = [dep for dep in deps if status_by_id.get(dep) != "completed"]
        if unmet:
            blocked_exists = True
            continue
        ready.append(task)
    return ready, not blocked_exists


def run_chunk_post_markdown_hook(root: Path, chunk: Artifact) -> tuple[bool, str]:
    config = load_workspace_config(root)
    hook_rel_path = _hook_markdown_path(config, "post_chunk_markdown")
    if not hook_rel_path:
        return True, "(no hook)"

    hook_path = root / hook_rel_path
    if not hook_path.exists():
        return False, f"hook file not found: {hook_rel_path}"

    if not is_executor_enabled(config):
        return False, "executor.enabled is false in .onward.config.yaml (executor disabled)"

    preflight_err = preflight_executor_command(config)
    if preflight_err:
        return False, preflight_err

    block = config.get("executor", {})
    if not isinstance(block, dict):
        block = {}
    command = clean_string(block.get("command")) or "onward-exec"
    command_args = block.get("args", [])
    if not isinstance(command_args, list):
        command_args = []
    cmd = [command, *[str(item) for item in command_args]]
    model = model_setting(config, "review_default", model_setting(config, "default", "opus-latest"))
    payload = {
        "type": "hook",
        "phase": "post_chunk_markdown",
        "model": model,
        "hook_path": hook_rel_path,
        "hook_body": hook_path.read_text(encoding="utf-8"),
        "chunk": chunk.metadata,
        "chunk_body": chunk.body,
    }
    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            input=json.dumps(with_schema_version(payload), indent=2, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return False, f"executor command not found: {command}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return False, stderr or f"exit code {result.returncode}"
    return True, ""


def run_pre_chunk_shell_hooks(root: Path, chunk: Artifact) -> tuple[bool, str]:
    """Shell commands once when ``onward work CHUNK-*`` starts, before the task loop."""
    config = load_workspace_config(root)
    commands = _hook_commands(config, "pre_chunk_shell")
    chunk_id = str(chunk.metadata.get("id", ""))
    env = {
        "ONWARD_CHUNK_ID": chunk_id,
        "ONWARD_CHUNK_TITLE": str(chunk.metadata.get("title", "")),
    }
    return _run_shell_hooks(root, commands, "pre_chunk_shell", env)


def work_chunk(root: Path, chunk: Artifact, config: dict[str, Any]) -> int:
    """Run all ready tasks in a chunk using :meth:`~onward.executor.Executor.execute_batch` per wave."""
    chunk_id = str(chunk.metadata.get("id", ""))
    if str(chunk.metadata.get("status", "")) == "completed":
        return 0

    preflight_err = preflight_executor_command(config)
    if preflight_err:
        print(f"Error: {preflight_err}")
        return 1

    sequential = work_sequential_by_default(config)
    if str(chunk.metadata.get("status", "")) in {"open", "in_progress"}:
        update_artifact_status(root, chunk, "in_progress")

    pre_chunk_ok, pre_chunk_log = run_pre_chunk_shell_hooks(root, chunk)
    if not pre_chunk_ok:
        print(f"pre_chunk_shell hook failed:\n{pre_chunk_log}")
        return 1

    while True:
        ready_tasks, all_resolved = ordered_ready_chunk_tasks(root, chunk_id)
        if not ready_tasks:
            if not all_resolved:
                print(f"Chunk {chunk_id} has unresolved task dependencies")
                return 1
            break

        eligible: list[Artifact] = []
        for candidate in ready_tasks:
            tid = str(candidate.metadata.get("id", ""))
            fresh = must_find_by_id(root, tid)
            run_count = int(fresh.metadata.get("run_count", 0))
            max_r = work_max_retries(config)
            if max_r > 0 and run_count >= max_r:
                print(
                    f"Warning: {tid} has reached run_count={run_count} "
                    f"(work.max_retries={max_r}); skipping. See docs/LIFECYCLE.md"
                )
                continue
            eligible.append(fresh)

        if not eligible:
            print(
                f"Chunk {chunk_id}: no task could run (all ready tasks hit work.max_retries). "
                "Use onward retry on a task or adjust work.max_retries. See docs/LIFECYCLE.md"
            )
            return 1

        if not sequential:
            eligible = eligible[:1]

        wave: list[PreparedTaskRun] = []
        for fresh in eligible:
            tid = str(fresh.metadata.get("id", ""))
            update_artifact_status(root, fresh, "in_progress")
            wave.append(_prepare_task_run(root, must_find_by_id(root, tid), config))

        executor = resolve_executor(config)
        ok, outcomes = _run_hooked_executor_batch(root, config, executor, wave)
        for run_id, task_ok in outcomes:
            print(f"Run {run_id}: {'completed' if task_ok else 'failed'}")
        if not ok:
            print(f"Stopping chunk work for {chunk_id} after task failure")
            print(
                f"Chunk {chunk_id} is usually still in_progress; fix the task or run "
                f"onward work {chunk_id} again. See docs/LIFECYCLE.md"
            )
            return 1

        if not sequential:
            ready_again, all_resolved_again = ordered_ready_chunk_tasks(root, chunk_id)
            if ready_again:
                print(
                    f"Chunk {chunk_id}: stopping after one task (work.sequential_by_default is false); "
                    "run onward work again to continue."
                )
                return 0
            if not all_resolved_again:
                print(f"Chunk {chunk_id} has unresolved task dependencies")
                return 1

    refreshed_chunk = must_find_by_id(root, chunk_id)
    if str(refreshed_chunk.metadata.get("status", "")) == "completed":
        print(f"Chunk {chunk_id} completed")
        return 0
    hook_ok, hook_error = run_chunk_post_markdown_hook(root, refreshed_chunk)
    if not hook_ok:
        print(f"Chunk {chunk_id} post hook failed: {hook_error}")
        return 1
    if str(refreshed_chunk.metadata.get("status", "")) in {"open", "in_progress"}:
        update_artifact_status(root, refreshed_chunk, "completed")
    print(f"Chunk {chunk_id} completed")
    return 0


def finalize_chunks_all_tasks_terminal(root: Path) -> tuple[list[str], list[str]]:
    """Move chunks to *completed* when every child task is terminal (completed/canceled).

    Runs ``post_chunk_markdown`` when configured, matching ``onward work CHUNK-*`` completion.
    Skips chunks with zero tasks. Returns ``(completed_chunk_ids, warnings)``.
    """
    artifacts = collect_artifacts(root)
    tasks_by_chunk: dict[str, list[Artifact]] = {}
    for a in artifacts:
        if str(a.metadata.get("type", "")) != "task":
            continue
        cid = str(a.metadata.get("chunk", ""))
        if not cid:
            continue
        tasks_by_chunk.setdefault(cid, []).append(a)

    completed: list[str] = []
    warnings: list[str] = []
    for a in artifacts:
        if str(a.metadata.get("type", "")) != "chunk":
            continue
        st = str(a.metadata.get("status", ""))
        if st not in {"open", "in_progress"}:
            continue
        chunk_id = str(a.metadata.get("id", ""))
        chunk_tasks = tasks_by_chunk.get(chunk_id, [])
        if not chunk_tasks:
            continue
        if any(str(t.metadata.get("status", "")) not in {"completed", "canceled"} for t in chunk_tasks):
            continue
        refreshed = must_find_by_id(root, chunk_id)
        hook_ok, hook_err = run_chunk_post_markdown_hook(root, refreshed)
        if not hook_ok:
            warnings.append(
                f"Chunk {chunk_id} has all tasks terminal but post hook failed ({hook_err}); chunk left open."
            )
            continue
        if str(refreshed.metadata.get("status", "")) in {"open", "in_progress"}:
            update_artifact_status(root, refreshed, "completed")
            completed.append(chunk_id)
    return completed, warnings


# ---------------------------------------------------------------------------
# Run queries
# ---------------------------------------------------------------------------


def collect_runs_for_target(root: Path, target_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Return run JSON records for ``target_id``, newest first (by ``started_at``), capped at ``limit``."""
    run_dir = root / ".onward/runs"
    if not run_dir.exists():
        return []
    pattern = f"RUN-*-{target_id}.json"
    matches = list(run_dir.glob(pattern))
    records: list[dict[str, Any]] = []
    for path in matches:
        try:
            records.append(read_run_json_record(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue

    def _sort_key(rec: dict[str, Any]) -> str:
        return str(rec.get("started_at") or "")

    records.sort(key=_sort_key, reverse=True)
    return records[:limit]


def latest_run_for(root: Path, target_id: str) -> dict[str, Any] | None:
    run_dir = root / ".onward/runs"
    if not run_dir.exists():
        return None
    pattern = f"RUN-*-{target_id}.json"
    matches = sorted(run_dir.glob(pattern), reverse=True)
    if not matches:
        return None
    try:
        return read_run_json_record(matches[0].read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def collect_run_records(root: Path) -> list[dict[str, Any]]:
    run_dir = root / ".onward/runs"
    if not run_dir.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("RUN-*.json")):
        try:
            records.append(read_run_json_record(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return records


# ---------------------------------------------------------------------------
# Plan review
# ---------------------------------------------------------------------------


def execute_plan_review(
    root: Path,
    plan: Artifact,
    model: str,
    label: str,
    prompt: str,
    *,
    executor_command: str | None = None,
    executor_args: list[str] | None = None,
    emit_errors: bool = True,
) -> tuple[bool, Path]:
    config = load_workspace_config(root)
    block = config.get("executor", {})
    if not isinstance(block, dict):
        block = {}
    if executor_command is not None:
        command = clean_string(executor_command) or "onward-exec"
        command_args = list(executor_args) if executor_args is not None else []
    else:
        command = clean_string(block.get("command")) or "onward-exec"
        command_args = block.get("args", [])
        if not isinstance(command_args, list):
            command_args = []
    cmd = [command, *[str(item) for item in command_args]]

    plan_id = str(plan.metadata.get("id", ""))
    timestamp = run_timestamp()

    review_dir = root / ".onward/reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / f"{plan_id}-{timestamp}-{label}.md"

    prompt_context = "\n".join([
        prompt.strip(),
        "",
        "---",
        "",
        "Plan metadata:",
        dump_simple_yaml(plan.metadata).rstrip(),
        "",
        "Plan body:",
        plan.body.strip(),
    ])

    payload = {
        "type": "review",
        "model": model,
        "plan_id": plan_id,
        "prompt": prompt_context,
        "plan_metadata": plan.metadata,
        "plan_body": plan.body,
    }

    env_override = str(os.environ.get("TRAIN_REVIEW_RESPONSE", "")).strip()
    if env_override:
        review_path.write_text(env_override, encoding="utf-8")
        return True, review_path

    if not is_executor_enabled(config):
        if emit_errors:
            print("Error: executor.enabled is false in .onward.config.yaml (executor disabled)")
        return False, review_path

    preflight_err = preflight_shell_invocation(command)
    if preflight_err:
        if emit_errors:
            print(f"Error: {preflight_err}")
        return False, review_path

    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            input=json.dumps(with_schema_version(payload), indent=2, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        if emit_errors:
            print(f"Error: executor command not found: {command}")
        return False, review_path
    except Exception as exc:  # noqa: BLE001
        if emit_errors:
            print(f"Error: {exc}")
        return False, review_path

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        if emit_errors:
            print(f"Error: review failed for {label} ({model}): {stderr or f'exit code {result.returncode}'}")
        return False, review_path

    output = (result.stdout or "").strip()
    if not output:
        output = f"## Review: {plan.metadata.get('title', plan_id)}\n\n### Overall Assessment: No output from reviewer\n"

    review_path.write_text(output + "\n", encoding="utf-8")
    return True, review_path
