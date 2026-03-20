from __future__ import annotations

import json
import os
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
    normalize_priority,
    now_iso,
    slugify,
)


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
            }
        )
    return {"tasks": tasks}


def run_split_model(
    artifact: Artifact,
    prompt_name: str,
    model: str,
    default_task_model: str,
) -> str:
    env_override = str(os.environ.get("TRAIN_SPLIT_RESPONSE", "")).strip()
    if env_override:
        return env_override
    if prompt_name == "split-plan.md":
        payload = _heuristic_split_plan_payload(artifact, model)
    else:
        payload = _heuristic_split_chunk_payload(artifact, default_task_model)
    return json.dumps(payload, indent=2)


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
    out: list[dict[str, Any]] = []
    for i, item in enumerate(items, start=1):
        title = clean_string(item.get("title"))
        description = clean_string(item.get("description"))
        if not title:
            raise ValueError(f"split validation failed: chunks[{i}].title is required")
        if not description:
            raise ValueError(f"split validation failed: chunks[{i}].description is required")
        model = clean_string(item.get("model")) or default_model
        out.append(
            {
                "title": title,
                "description": description,
                "priority": normalize_priority(item.get("priority")),
                "model": model,
            }
        )
    return out


def normalize_task_candidates(items: list[dict[str, Any]], default_model: str) -> list[dict[str, Any]]:
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
        out.append(
            {
                "title": title,
                "description": description,
                "acceptance": acceptance,
                "model": model,
                "human": normalize_bool(item.get("human")),
            }
        )
    return out


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
    for chunk_id, candidate in zip(chunk_ids, candidates):
        target = plan_dir / "chunks" / f"{chunk_id}-{slugify(candidate['title'])}.md"
        metadata = {
            "id": chunk_id,
            "type": "chunk",
            "plan": plan_id,
            "project": artifact_project(plan_artifact),
            "title": candidate["title"],
            "status": "open",
            "description": candidate["description"],
            "priority": candidate["priority"],
            "model": candidate["model"],
            "created_at": now,
            "updated_at": now,
        }
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
                "- None specified.",
                "",
                "# Expected files/systems involved",
                "",
                "- Determine during implementation.",
                "",
                "# Completion criteria",
                "",
                f"- {candidate['description']}",
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
    for task_id, candidate in zip(task_ids, candidates):
        target = plan_dir / "tasks" / f"{task_id}-{slugify(candidate['title'])}.md"
        metadata = {
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
            "depends_on": [],
            "blocked_by": [],
            "files": [],
            "acceptance": candidate["acceptance"],
            "created_at": now,
            "updated_at": now,
        }
        acceptance_lines = "\n".join(f"- {item}" for item in candidate["acceptance"])
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
                "- Determine during implementation.",
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
