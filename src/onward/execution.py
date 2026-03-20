from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from onward.artifacts import (
    Artifact,
    collect_artifacts,
    find_by_id,
    must_find_by_id,
    read_notes,
    update_artifact_status,
)
from onward.config import (
    is_executor_enabled,
    load_workspace_config,
    model_setting,
    resolve_model_alias,
    work_require_success_ack,
)
from onward.executor_ack import find_task_success_ack
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


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------


def _execute_task_run(root: Path, task: Artifact) -> tuple[bool, str]:
    config = load_workspace_config(root)
    block = config.get("executor", {})
    if not isinstance(block, dict):
        block = {}
    command = clean_string(block.get("command")) or "onward-exec"
    command_args = block.get("args", [])
    if not isinstance(command_args, list):
        command_args = []
    cmd = [command, *[str(item) for item in command_args]]

    default_model = model_setting(config, "default", "opus-latest")
    task_model = clean_string(task.metadata.get("model")) or default_model
    model = resolve_model_alias(task_model)

    task_id = str(task.metadata.get("id", ""))
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
        "executor": command,
        "started_at": started_at,
        "finished_at": None,
        "log_path": str(run_log.relative_to(root)),
        "error": "",
    }
    run_json.write_text(dump_run_json_record(run_record), encoding="utf-8")

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
    payload: dict[str, Any] = {
        "type": "task",
        "run_id": run_id,
        "task": task.metadata,
        "body": task.body,
        "notes": notes if notes.strip() else None,
        "notes_hint": (
            f"To add a note to this task, run: onward note {task_id} \"your note\". "
            f"To read existing notes: onward note {task_id}"
        ),
        "chunk": chunk_context,
        "plan": plan_context,
    }
    log_sections: list[str] = [f"$ {' '.join(cmd)}"]
    error = ""
    ok = False
    ack_obj: dict[str, Any] | None = None
    pre_shell = _hook_commands(config, "pre_task_shell")
    post_shell = _hook_commands(config, "post_task_shell")
    pre_md = _hook_markdown_path(config, "pre_task_markdown")
    post_md = _hook_markdown_path(config, "post_task_markdown")

    hook_env = {
        "ONWARD_RUN_ID": run_id,
        "ONWARD_TASK_ID": task_id,
        "ONWARD_TASK_TITLE": str(task.metadata.get("title", "")),
    }

    pre_shell_ok, pre_shell_log = _run_shell_hooks(root, pre_shell, "pre_task_shell", hook_env)
    log_sections.append(pre_shell_log)
    if not pre_shell_ok:
        error = "pre_task_shell hook failed"
    elif not is_executor_enabled(config):
        error = "executor.enabled is false in .onward.config.yaml (executor disabled)"
    else:
        pre_md_ok, pre_md_log = _run_markdown_hook(root, cmd, pre_md, "pre_task_markdown", model, task, run_id)
        log_sections.append(pre_md_log)
        if not pre_md_ok:
            error = "pre_task_markdown hook failed"

    if not error:
        try:
            child_env = {**os.environ, "ONWARD_RUN_ID": run_id}
            result = subprocess.run(
                cmd,
                cwd=root,
                input=json.dumps(with_schema_version(payload), indent=2, ensure_ascii=False),
                text=True,
                capture_output=True,
                check=False,
                env=child_env,
            )
            if result.stdout:
                log_sections.append("[task stdout]\n" + result.stdout.rstrip())
            if result.stderr:
                log_sections.append("[task stderr]\n" + result.stderr.rstrip())
            ok = result.returncode == 0
            if ok:
                found, ack_err, ack_obj = find_task_success_ack(
                    result.stdout or "",
                    result.stderr or "",
                    run_id,
                )
                if work_require_success_ack(config) and not found:
                    ok = False
                    error = ack_err
            else:
                error = f"executor exited with code {result.returncode}"
        except FileNotFoundError:
            error = f"executor command not found: {command}"
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

    if ok and not error:
        post_shell_ok, post_shell_log = _run_shell_hooks(root, post_shell, "post_task_shell", hook_env)
        log_sections.append(post_shell_log)
        if not post_shell_ok:
            ok = False
            error = "post_task_shell hook failed"
    if ok and not error:
        post_md_ok, post_md_log = _run_markdown_hook(root, cmd, post_md, "post_task_markdown", model, task, run_id)
        log_sections.append(post_md_log)
        if not post_md_ok:
            ok = False
            error = "post_task_markdown hook failed"

    if error:
        log_sections.append(f"[error] {error}")
    run_log.write_text("\n\n".join(section.rstrip() for section in log_sections if section).rstrip() + "\n", encoding="utf-8")

    finished_at = now_iso()
    run_record["status"] = "completed" if ok else "failed"
    run_record["finished_at"] = finished_at
    run_record["error"] = error
    if ack_obj is not None:
        run_record["success_ack"] = ack_obj
    run_json.write_text(dump_run_json_record(run_record), encoding="utf-8")

    ongoing = load_ongoing(root)
    remaining = [
        item
        for item in ongoing.get("active_runs", [])
        if str(item.get("id", "")) != run_id
    ]
    ongoing["active_runs"] = remaining
    _write_ongoing(root, ongoing)
    return ok, run_id


def work_task(root: Path, task: Artifact) -> tuple[bool, str]:
    if str(task.metadata.get("type", "")) != "task":
        raise ValueError(f"{task.metadata.get('id')} is not a task")

    preflight_err = preflight_executor_command(load_workspace_config(root))
    if preflight_err:
        raise ValueError(preflight_err)

    current = str(task.metadata.get("status", ""))
    if current == "completed":
        return True, ""
    if current not in {"open", "in_progress"}:
        if current == "canceled":
            raise ValueError(
                "cannot work task in state 'canceled' "
                "(only open or in_progress tasks can run; edit status or add a follow-up task). "
                "See docs/LIFECYCLE.md"
            )
        raise ValueError(
            f"cannot work task in state {current!r} "
            f"(expected open or in_progress). See docs/LIFECYCLE.md"
        )

    update_artifact_status(root, task, "in_progress")
    ok, run_id = _execute_task_run(root, task)
    refreshed = must_find_by_id(root, str(task.metadata.get("id", "")))
    update_artifact_status(root, refreshed, "completed" if ok else "open")
    return ok, run_id


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
        deps = as_str_list(task.metadata.get("depends_on"))
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
    model = resolve_model_alias(model_setting(config, "review_default", model_setting(config, "default", "opus-latest")))
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
