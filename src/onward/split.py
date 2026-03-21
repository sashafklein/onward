from __future__ import annotations

import json
import os
import subprocess
from collections import deque
from pathlib import Path
from typing import Any

from onward.artifacts import (
    Artifact,
    artifact_project,
    find_plan_dir,
    format_artifact,
    next_ids,
)
from onward.util import (
    clean_string,
    extract_markdown_list_items,
    markdown_section,
    normalize_acceptance,
    normalize_bool,
    normalize_effort,
    normalize_priority,
    now_iso,
    slugify,
)
from onward.config import is_executor_enabled
from onward.executor_payload import with_schema_version
from onward.preflight import preflight_executor_command


def _normalize_files_touch_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {"must": [], "likely": [], "deferred": []}
    out: dict[str, list[str]] = {"must": [], "likely": [], "deferred": []}
    for key in ("must", "likely", "deferred"):
        raw = value.get(key)
        if isinstance(raw, list):
            out[key] = [str(x).strip() for x in raw if str(x).strip()]
        elif isinstance(raw, str) and raw.strip():
            out[key] = [raw.strip()]
    return out


def _normalize_task_files_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_dep_indices(raw: Any, n_items: int, self_index: int) -> list[int]:
    if not isinstance(raw, list):
        return []
    out: list[int] = []
    for x in raw:
        try:
            j = int(x)
        except (TypeError, ValueError):
            continue
        if j < 0 or j >= n_items or j == self_index:
            continue
        if j not in out:
            out.append(j)
    return out


def _format_chunk_files_section(files: dict[str, list[str]]) -> str:
    must = files.get("must") or []
    likely = files.get("likely") or []
    deferred = files.get("deferred") or []
    if not must and not likely and not deferred:
        return "- Determine during implementation."
    parts: list[str] = []
    if must:
        parts.append("**Must touch:**")
        parts.extend(f"- `{p}`" for p in must)
        parts.append("")
    if likely:
        parts.append("**Likely:**")
        parts.extend(f"- `{p}`" for p in likely)
        parts.append("")
    if deferred:
        parts.append("**Deferred / out of scope for this chunk:**")
        parts.extend(f"- `{p}`" for p in deferred)
    return "\n".join(parts).rstrip()


def _heuristic_split_plan_payload(artifact: Artifact, default_model: str) -> dict[str, Any]:
    strategy_items = extract_markdown_list_items(markdown_section(artifact.body, "Chunking strategy"))
    goal_items = extract_markdown_list_items(markdown_section(artifact.body, "Goals"))
    seeds = strategy_items or goal_items
    if not seeds:
        seeds = [f"Implement {artifact.metadata.get('title', 'plan scope')}"]
    chunks: list[dict[str, Any]] = []
    for seed in seeds:
        chunks.append(
            {
                "title": seed[:120].strip(),
                "description": seed.strip(),
                "priority": "medium",
                "model": default_model,
                "depends_on_index": [],
                "files": {"must": [], "likely": [], "deferred": []},
                "acceptance": [seed.strip()],
            }
        )
    return {"chunks": chunks}


def _heuristic_split_chunk_payload(artifact: Artifact, default_model: str) -> dict[str, Any]:
    scope_items = extract_markdown_list_items(markdown_section(artifact.body, "Scope"))
    completion_items = extract_markdown_list_items(markdown_section(artifact.body, "Completion criteria"))
    seeds = scope_items or completion_items
    if not seeds:
        seeds = [f"Implement {artifact.metadata.get('title', 'chunk scope')}"]
    tasks: list[dict[str, Any]] = []
    for seed in seeds:
        tasks.append(
            {
                "title": seed[:120].strip(),
                "description": seed.strip(),
                "acceptance": [seed.strip()],
                "model": default_model,
                "human": False,
                "depends_on_index": [],
                "files": [],
                "effort": "",
            }
        )
    return {"tasks": tasks}


def _run_split_executor(
    root: Path,
    config: dict[str, Any],
    artifact: Artifact,
    prompt_name: str,
    split_model: str,
) -> str:
    preflight_err = preflight_executor_command(config)
    if preflight_err:
        raise ValueError(preflight_err)
    if not is_executor_enabled(config):
        raise ValueError(
            "executor.enabled is false in .onward.config.yaml (cannot run AI split; use --heuristic)"
        )

    block = config.get("executor", {})
    if not isinstance(block, dict):
        block = {}
    command = clean_string(block.get("command")) or "onward-exec"
    command_args = block.get("args", [])
    if not isinstance(command_args, list):
        command_args = []
    cmd = [command, *[str(item) for item in command_args]]

    prompt_path = root / ".onward" / "prompts" / prompt_name
    if not prompt_path.is_file():
        raise ValueError(f"split prompt not found: {prompt_path.relative_to(root)}")

    artifact_type = str(artifact.metadata.get("type", ""))
    if artifact_type == "plan":
        split_type = "plan"
        model_for_alias = split_model
    elif artifact_type == "chunk":
        split_type = "chunk"
        model_for_alias = split_model
    else:
        raise ValueError(f"unexpected artifact type for split: {artifact_type!r}")

    payload: dict[str, Any] = {
        "type": "split",
        "model": model_for_alias.strip(),
        "prompt": prompt_path.read_text(encoding="utf-8"),
        "artifact_metadata": dict(artifact.metadata),
        "artifact_body": artifact.body,
        "split_type": split_type,
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
        raise ValueError(f"executor command not found: {command}") from None

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        extra = f": {detail}" if detail else ""
        raise ValueError(f"split executor exited with code {result.returncode}{extra}")

    raw = (result.stdout or "").strip()
    if not raw:
        raise ValueError("split executor produced empty stdout (expected JSON)")
    return raw


def run_split_model(
    root: Path,
    artifact: Artifact,
    prompt_name: str,
    split_model: str,
    default_task_model: str,
    *,
    heuristic: bool,
    config: dict[str, Any],
) -> str:
    env_override = str(os.environ.get("TRAIN_SPLIT_RESPONSE", "")).strip()
    if env_override:
        return env_override
    if heuristic:
        if prompt_name == "split-plan.md":
            payload = _heuristic_split_plan_payload(artifact, split_model)
        else:
            payload = _heuristic_split_chunk_payload(artifact, default_task_model)
        return json.dumps(payload, indent=2)
    return _run_split_executor(root, config, artifact, prompt_name, split_model)


def parse_split_payload(raw: str, key: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid split JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("invalid split JSON: root must be an object")
    items = payload.get(key)
    if not isinstance(items, list) or not items:
        raise ValueError(f"invalid split JSON: '{key}' must be a non-empty array")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"invalid split JSON: {key}[{i}] must be an object")
        out.append(item)
    return out


def normalize_chunk_candidates(items: list[dict[str, Any]], default_model: str) -> list[dict[str, Any]]:
    n = len(items)
    out: list[dict[str, Any]] = []
    for i, item in enumerate(items, start=1):
        title = clean_string(item.get("title"))
        description = clean_string(item.get("description"))
        if not title:
            raise ValueError(f"split validation failed: chunks[{i}].title is required")
        if not description:
            raise ValueError(f"split validation failed: chunks[{i}].description is required")
        model = clean_string(item.get("model")) or default_model
        acceptance = normalize_acceptance(item.get("acceptance"))
        if not acceptance:
            acceptance = [description]
        files = _normalize_files_touch_map(item.get("files"))
        idx0 = i - 1
        depends_on_index = _coerce_dep_indices(item.get("depends_on_index"), n, idx0)
        out.append(
            {
                "title": title,
                "description": description,
                "priority": normalize_priority(item.get("priority")),
                "model": model,
                "depends_on_index": depends_on_index,
                "files": files,
                "acceptance": acceptance,
            }
        )
    return out


def normalize_task_candidates(items: list[dict[str, Any]], default_model: str) -> list[dict[str, Any]]:
    n = len(items)
    out: list[dict[str, Any]] = []
    for i, item in enumerate(items, start=1):
        title = clean_string(item.get("title"))
        description = clean_string(item.get("description"))
        acceptance = normalize_acceptance(item.get("acceptance"))
        if not title:
            raise ValueError(f"split validation failed: tasks[{i}].title is required")
        if not description:
            raise ValueError(f"split validation failed: tasks[{i}].description is required")
        if not acceptance:
            raise ValueError(f"split validation failed: tasks[{i}].acceptance is required")
        model = clean_string(item.get("model")) or default_model
        if not model:
            raise ValueError(f"split validation failed: tasks[{i}].model is required")
        idx0 = i - 1
        depends_on_index = _coerce_dep_indices(item.get("depends_on_index"), n, idx0)
        files = _normalize_task_files_list(item.get("files"))
        effort = normalize_effort(item.get("effort"))
        out.append(
            {
                "title": title,
                "description": description,
                "acceptance": acceptance,
                "model": model,
                "human": normalize_bool(item.get("human")),
                "depends_on_index": depends_on_index,
                "files": files,
                "effort": effort,
            }
        )
    return out


def _dependency_graph_has_cycle(n: int, items: list[dict[str, Any]]) -> bool:
    """True if depends_on edges (j must finish before i) contain a directed cycle."""
    edges: set[tuple[int, int]] = set()
    for i, item in enumerate(items):
        for j in item.get("depends_on_index", []):
            if not isinstance(j, int) or j < 0 or j >= n or j == i:
                continue
            edges.add((j, i))
    adj: list[list[int]] = [[] for _ in range(n)]
    indeg = [0] * n
    for j, i in edges:
        adj[j].append(i)
        indeg[i] += 1
    q: deque[int] = deque(k for k in range(n) if indeg[k] == 0)
    seen = 0
    while q:
        u = q.popleft()
        seen += 1
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return seen != n


def validate_split_output(
    items: list[dict[str, Any]],
    split_type: str,
) -> tuple[list[str], list[str]]:
    """Return (warnings, errors) for normalized split candidates."""
    warnings: list[str] = []
    errors: list[str] = []
    n = len(items)

    if split_type == "plan":
        if n < 2:
            warnings.append(f"split produced only {n} chunk(s); consider more than one for parallel work")
        if n > 15:
            warnings.append(f"split produced {n} chunks (unusually many); consider merging related work")
        titles = [clean_string(x.get("title")) for x in items]
        if len(titles) != len(set(titles)):
            errors.append("duplicate chunk titles in split output (would collide on disk)")
        for i, item in enumerate(items, start=1):
            files = item.get("files") or {}
            if isinstance(files, dict):
                total = len(files.get("must") or []) + len(files.get("likely") or []) + len(files.get("deferred") or [])
                if total > 35:
                    warnings.append(f"chunks[{i}] lists {total} file paths (target ~20–30); consider narrowing")
        if n >= 2 and _dependency_graph_has_cycle(n, items):
            errors.append("chunk depends_on_index contains a cycle")

    elif split_type == "chunk":
        if n > 10:
            warnings.append(f"split produced {n} tasks in one chunk (many); consider fewer, larger tasks")
        titles = [clean_string(x.get("title")) for x in items]
        if len(titles) != len(set(titles)):
            errors.append("duplicate task titles in split output (would collide on disk)")
        for i, item in enumerate(items, start=1):
            t_files = item.get("files") or []
            if isinstance(t_files, list) and t_files:
                fc = len(t_files)
                if fc > 9:
                    errors.append(f"tasks[{i}] lists {fc} files (>9); split this task")
                elif fc >= 7:
                    warnings.append(f"tasks[{i}] lists {fc} files (prefer ≤6)")
        if n >= 1 and _dependency_graph_has_cycle(n, items):
            errors.append("task depends_on_index contains a cycle")

    return warnings, errors


def prepare_chunk_writes(
    root: Path,
    plan_artifact: Artifact,
    candidates: list[dict[str, Any]],
) -> list[tuple[str, Path, str]]:
    plan_id = str(plan_artifact.metadata.get("id"))
    plan_dir = find_plan_dir(root, plan_id)
    chunk_ids = next_ids(root, "CHUNK", len(candidates))
    now = now_iso()
    writes: list[tuple[str, Path, str]] = []
    for idx, (chunk_id, candidate) in enumerate(zip(chunk_ids, candidates)):
        target = plan_dir / "chunks" / f"{chunk_id}-{slugify(candidate['title'])}.md"
        dep_ids: list[str] = []
        for j in candidate.get("depends_on_index", []):
            if isinstance(j, int) and 0 <= j < len(chunk_ids) and j != idx:
                cid = chunk_ids[j]
                if cid not in dep_ids:
                    dep_ids.append(cid)
        metadata: dict[str, Any] = {
            "id": chunk_id,
            "type": "chunk",
            "plan": plan_id,
            "project": artifact_project(plan_artifact),
            "title": candidate["title"],
            "status": "open",
            "description": candidate["description"],
            "priority": candidate["priority"],
            "model": candidate["model"],
            "depends_on": dep_ids,
            "created_at": now,
            "updated_at": now,
        }
        ceff = normalize_effort(candidate.get("effort", ""))
        if ceff:
            metadata["effort"] = ceff
        cefn = candidate.get("estimated_files")
        if isinstance(cefn, int) and cefn >= 0:
            metadata["estimated_files"] = cefn
        files_map = candidate.get("files") or {"must": [], "likely": [], "deferred": []}
        acceptance_lines = "\n".join(f"- {a}" for a in candidate.get("acceptance", []))
        files_section = _format_chunk_files_section(files_map)
        deps_body = "\n".join(f"- {d}" for d in dep_ids) if dep_ids else "- None specified."
        body = "\n".join(
            [
                "# Summary",
                "",
                candidate["description"],
                "",
                "# Scope",
                "",
                f"- {candidate['description']}",
                "",
                "# Out of scope",
                "",
                "- None specified.",
                "",
                "# Dependencies",
                "",
                deps_body,
                "",
                "# Expected files/systems involved",
                "",
                files_section,
                "",
                "# Completion criteria",
                "",
                acceptance_lines,
                "",
                "# Notes",
                "",
                "",
            ]
        )
        writes.append((chunk_id, target, format_artifact(metadata, body)))
    return writes


def prepare_task_writes(
    root: Path,
    chunk_artifact: Artifact,
    candidates: list[dict[str, Any]],
) -> list[tuple[str, Path, str]]:
    plan_id = str(chunk_artifact.metadata.get("plan"))
    chunk_id = str(chunk_artifact.metadata.get("id"))
    plan_dir = find_plan_dir(root, plan_id)
    task_ids = next_ids(root, "TASK", len(candidates))
    now = now_iso()
    writes: list[tuple[str, Path, str]] = []
    for idx, (task_id, candidate) in enumerate(zip(task_ids, candidates)):
        target = plan_dir / "tasks" / f"{task_id}-{slugify(candidate['title'])}.md"
        dep_ids: list[str] = []
        for j in candidate.get("depends_on_index", []):
            if isinstance(j, int) and 0 <= j < len(task_ids) and j != idx:
                tid = task_ids[j]
                if tid not in dep_ids:
                    dep_ids.append(tid)
        t_files = candidate.get("files") or []
        metadata: dict[str, Any] = {
            "id": task_id,
            "type": "task",
            "plan": plan_id,
            "chunk": chunk_id,
            "project": artifact_project(chunk_artifact),
            "title": candidate["title"],
            "status": "open",
            "description": candidate["description"],
            "human": candidate["human"],
            "model": candidate["model"],
            "executor": "onward-exec",
            "depends_on": dep_ids,
            "files": t_files,
            "acceptance": candidate["acceptance"],
            "created_at": now,
            "updated_at": now,
        }
        effort = normalize_effort(candidate.get("effort", ""))
        if effort:
            metadata["effort"] = effort
        acceptance_lines = "\n".join(f"- {item}" for item in candidate["acceptance"])
        if t_files:
            files_lines = "\n".join(f"- `{p}`" for p in t_files)
        else:
            files_lines = "- Determine during implementation."
        body = "\n".join(
            [
                "# Context",
                "",
                candidate["description"],
                "",
                "# Scope",
                "",
                f"- {candidate['description']}",
                "",
                "# Out of scope",
                "",
                "- None specified.",
                "",
                "# Files to inspect",
                "",
                files_lines,
                "",
                "# Implementation notes",
                "",
                "- Keep the change scoped to this task.",
                "",
                "# Acceptance criteria",
                "",
                acceptance_lines,
                "",
                "# Handoff notes",
                "",
                "",
            ]
        )
        writes.append((task_id, target, format_artifact(metadata, body)))
    return writes


def assert_writes_safe(root: Path, writes: list[tuple[str, Path, str]]) -> None:
    seen: set[Path] = set()
    for _artifact_id, path, _content in writes:
        if path in seen:
            raise ValueError(f"split write collision: duplicate output path {path.relative_to(root)}")
        seen.add(path)
        if path.exists():
            raise ValueError(f"split write collision: target already exists {path.relative_to(root)}")
