from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from onward.artifacts import (
    Artifact,
    _collect_artifacts,
    _find_by_id,
    _must_find_by_id,
    _read_notes,
    _update_artifact_status,
)
from onward.config import _config_model, _load_config, _model_alias, _ralph_enabled
from onward.util import (
    _as_str_list,
    _clean_string,
    _dump_simple_yaml,
    _now_iso,
    _parse_simple_yaml,
    _run_timestamp,
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


def _run_shell_hooks(root: Path, commands: list[str], phase: str) -> tuple[bool, str]:
    if not commands:
        return True, f"[{phase}]\n(no hooks)"

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
            input=json.dumps(payload, indent=2),
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


def _load_ongoing(root: Path) -> dict[str, Any]:
    path = root / ".onward/ongoing.json"
    if not path.exists():
        return {"version": 1, "updated_at": _now_iso(), "active_runs": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = {"version": 1, "updated_at": _now_iso(), "active_runs": []}
    if not isinstance(payload, dict):
        payload = {"version": 1, "updated_at": _now_iso(), "active_runs": []}
    if not isinstance(payload.get("active_runs"), list):
        payload["active_runs"] = []
    return payload


def _write_ongoing(root: Path, payload: dict[str, Any]) -> None:
    payload["updated_at"] = _now_iso()
    path = root / ".onward/ongoing.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------


def _execute_task_run(root: Path, task: Artifact) -> tuple[bool, str]:
    config = _load_config(root)
    ralph = config.get("ralph", {})
    if not isinstance(ralph, dict):
        ralph = {}
    command = _clean_string(ralph.get("command")) or "ralph"
    command_args = ralph.get("args", [])
    if not isinstance(command_args, list):
        command_args = []
    cmd = [command, *[str(item) for item in command_args]]

    default_model = _config_model(config, "default", "opus-latest")
    task_model = _clean_string(task.metadata.get("model")) or default_model
    model = _model_alias(task_model)

    task_id = str(task.metadata.get("id", ""))
    run_id = f"RUN-{_run_timestamp()}-{task_id}"
    run_dir = root / ".onward/runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / f"{run_id}.json"
    run_log = run_dir / f"{run_id}.log"

    started_at = _now_iso()
    run_record: dict[str, Any] = {
        "id": run_id,
        "type": "run",
        "target": task_id,
        "plan": task.metadata.get("plan"),
        "chunk": task.metadata.get("chunk"),
        "status": "running",
        "model": model,
        "executor": "ralph",
        "started_at": started_at,
        "finished_at": None,
        "log_path": str(run_log.relative_to(root)),
        "error": "",
    }
    run_json.write_text(_dump_simple_yaml(run_record), encoding="utf-8")

    ongoing = _load_ongoing(root)
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

    notes = _read_notes(root, task_id)
    chunk_context: dict[str, Any] | None = None
    plan_context: dict[str, Any] | None = None
    chunk_id = _clean_string(task.metadata.get("chunk"))
    plan_id = _clean_string(task.metadata.get("plan"))
    if chunk_id:
        chunk_art = _find_by_id(root, chunk_id)
        if chunk_art:
            chunk_context = {"metadata": chunk_art.metadata, "body": chunk_art.body}
    if plan_id:
        plan_art = _find_by_id(root, plan_id)
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
    pre_shell = _hook_commands(config, "pre_task_shell")
    post_shell = _hook_commands(config, "post_task_shell")
    pre_md = _hook_markdown_path(config, "pre_task_markdown")
    post_md = _hook_markdown_path(config, "post_task_markdown")

    pre_shell_ok, pre_shell_log = _run_shell_hooks(root, pre_shell, "pre_task_shell")
    log_sections.append(pre_shell_log)
    if not pre_shell_ok:
        error = "pre_task_shell hook failed"
    elif not _ralph_enabled(config):
        error = "ralph.enabled is false in .onward.config.yaml (executor disabled)"
    else:
        pre_md_ok, pre_md_log = _run_markdown_hook(root, cmd, pre_md, "pre_task_markdown", model, task, run_id)
        log_sections.append(pre_md_log)
        if not pre_md_ok:
            error = "pre_task_markdown hook failed"

    if not error:
        try:
            result = subprocess.run(
                cmd,
                cwd=root,
                input=json.dumps(payload, indent=2),
                text=True,
                capture_output=True,
                check=False,
            )
            if result.stdout:
                log_sections.append("[task stdout]\n" + result.stdout.rstrip())
            if result.stderr:
                log_sections.append("[task stderr]\n" + result.stderr.rstrip())
            ok = result.returncode == 0
            if not ok:
                error = f"executor exited with code {result.returncode}"
        except FileNotFoundError:
            error = f"executor command not found: {command}"
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

    if ok and not error:
        post_shell_ok, post_shell_log = _run_shell_hooks(root, post_shell, "post_task_shell")
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

    finished_at = _now_iso()
    run_record["status"] = "completed" if ok else "failed"
    run_record["finished_at"] = finished_at
    run_record["error"] = error
    run_json.write_text(_dump_simple_yaml(run_record), encoding="utf-8")

    ongoing = _load_ongoing(root)
    remaining = [
        item
        for item in ongoing.get("active_runs", [])
        if str(item.get("id", "")) != run_id
    ]
    ongoing["active_runs"] = remaining
    _write_ongoing(root, ongoing)
    return ok, run_id


def _work_task(root: Path, task: Artifact) -> tuple[bool, str]:
    if str(task.metadata.get("type", "")) != "task":
        raise ValueError(f"{task.metadata.get('id')} is not a task")
    current = str(task.metadata.get("status", ""))
    if current == "completed":
        return True, ""
    if current not in {"open", "in_progress"}:
        raise ValueError(f"cannot work task in state '{current}'")

    _update_artifact_status(root, task, "in_progress")
    ok, run_id = _execute_task_run(root, task)
    refreshed = _must_find_by_id(root, str(task.metadata.get("id", "")))
    _update_artifact_status(root, refreshed, "completed" if ok else "open")
    return ok, run_id


def _ordered_ready_chunk_tasks(root: Path, chunk_id: str) -> tuple[list[Artifact], bool]:
    artifacts = _collect_artifacts(root)
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
        deps = _as_str_list(task.metadata.get("depends_on"))
        unmet = [dep for dep in deps if status_by_id.get(dep) != "completed"]
        if unmet:
            blocked_exists = True
            continue
        ready.append(task)
    return ready, not blocked_exists


def _run_chunk_post_markdown_hook(root: Path, chunk: Artifact) -> tuple[bool, str]:
    config = _load_config(root)
    hook_rel_path = _hook_markdown_path(config, "post_chunk_markdown")
    if not hook_rel_path:
        return True, "(no hook)"

    hook_path = root / hook_rel_path
    if not hook_path.exists():
        return False, f"hook file not found: {hook_rel_path}"

    if not _ralph_enabled(config):
        return False, "ralph.enabled is false in .onward.config.yaml (executor disabled)"

    ralph = config.get("ralph", {})
    if not isinstance(ralph, dict):
        ralph = {}
    command = _clean_string(ralph.get("command")) or "ralph"
    command_args = ralph.get("args", [])
    if not isinstance(command_args, list):
        command_args = []
    cmd = [command, *[str(item) for item in command_args]]
    model = _model_alias(_config_model(config, "review_default", _config_model(config, "default", "opus-latest")))
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
            input=json.dumps(payload, indent=2),
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


# ---------------------------------------------------------------------------
# Run queries
# ---------------------------------------------------------------------------


def _latest_run_for(root: Path, target_id: str) -> dict[str, Any] | None:
    run_dir = root / ".onward/runs"
    if not run_dir.exists():
        return None
    pattern = f"RUN-*-{target_id}.json"
    matches = sorted(run_dir.glob(pattern), reverse=True)
    if not matches:
        return None
    try:
        return _parse_simple_yaml(matches[0].read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _collect_run_records(root: Path) -> list[dict[str, Any]]:
    run_dir = root / ".onward/runs"
    if not run_dir.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("RUN-*.json")):
        try:
            records.append(_parse_simple_yaml(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return records


# ---------------------------------------------------------------------------
# Plan review
# ---------------------------------------------------------------------------


def _execute_plan_review(
    root: Path,
    plan: Artifact,
    model: str,
    label: str,
    prompt: str,
) -> tuple[bool, Path]:
    config = _load_config(root)
    ralph = config.get("ralph", {})
    if not isinstance(ralph, dict):
        ralph = {}
    command = _clean_string(ralph.get("command")) or "ralph"
    command_args = ralph.get("args", [])
    if not isinstance(command_args, list):
        command_args = []
    cmd = [command, *[str(item) for item in command_args]]

    plan_id = str(plan.metadata.get("id", ""))
    timestamp = _run_timestamp()

    review_dir = root / ".onward/reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / f"{plan_id}-{timestamp}-{label}.md"

    prompt_context = "\n".join([
        prompt.strip(),
        "",
        "---",
        "",
        "Plan metadata:",
        _dump_simple_yaml(plan.metadata).rstrip(),
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

    if not _ralph_enabled(config):
        print("Error: ralph.enabled is false in .onward.config.yaml (executor disabled)")
        return False, review_path

    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            input=json.dumps(payload, indent=2),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        print(f"Error: executor command not found: {command}")
        return False, review_path
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return False, review_path

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        print(f"Error: review failed for {label} ({model}): {stderr or f'exit code {result.returncode}'}")
        return False, review_path

    output = (result.stdout or "").strip()
    if not output:
        output = f"## Review: {plan.metadata.get('title', plan_id)}\n\n### Overall Assessment: No output from reviewer\n"

    review_path.write_text(output + "\n", encoding="utf-8")
    return True, review_path
