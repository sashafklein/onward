from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onward.config import MODEL_ALIASES, WorkspaceLayout, load_artifact_template, load_workspace_config, model_setting
from onward.util import (
    as_str_list,
    colorize,
    dump_simple_yaml,
    now_iso,
    parse_simple_yaml,
    read_run_json_record,
    slugify,
    split_frontmatter,
    status_color,
)

REQUIRED_FIELDS = {
    "plan": ["id", "type", "title", "status", "created_at", "updated_at"],
    "chunk": ["id", "type", "plan", "title", "status", "created_at", "updated_at"],
    "task": ["id", "type", "plan", "chunk", "title", "status", "created_at", "updated_at"],
}

# Optional fields recognized per artifact type — used to detect unknown frontmatter keys.
KNOWN_FIELDS: dict[str, list[str]] = {
    "plan": ["project", "priority", "model", "description", "linear_id", "linear_identifier", "linear_synced_at"],
    "chunk": ["project", "priority", "model", "effort", "complexity", "estimated_files", "description"],
    "task": [
        "project",
        "priority",
        "model",
        "executor",
        "effort",
        "complexity",
        "human",
        "depends_on",
        "blocked_by",
        "description",
        "run_count",
        "last_run_status",
    ],
}

_VALID_STATUSES = frozenset({"open", "in_progress", "completed", "canceled", "failed"})
_VALID_PRIORITIES = frozenset({"high", "medium", "low"})
_VALID_EFFORT_VALUES = frozenset({"xs", "s", "m", "l", "xl", "low", "medium", "high"})
_KNOWN_MODEL_PREFIXES = ("claude-", "codex-")


def _validate_status(value: Any) -> str | None:
    s = str(value).strip()
    if s not in _VALID_STATUSES:
        return f"invalid status '{s}' (expected: {', '.join(sorted(_VALID_STATUSES))})"
    return None


def _validate_priority(value: Any) -> str | None:
    s = str(value).strip().lower()
    if s not in _VALID_PRIORITIES:
        return f"invalid priority '{value}' (expected: high, medium, low)"
    return None


def _validate_effort(value: Any) -> str | None:
    s = str(value).strip().lower()
    if s not in _VALID_EFFORT_VALUES:
        return f"invalid effort/complexity '{value}' (expected: xs, s, m, l, xl)"
    return None


def _validate_model(value: Any) -> str | None:
    s = str(value).strip()
    if not s:
        return "model must be a non-empty string"
    s_lower = s.lower()
    if s_lower in MODEL_ALIASES:
        return None
    if any(s_lower.startswith(prefix) for prefix in _KNOWN_MODEL_PREFIXES):
        return None
    return f"unrecognized model '{s}' (expected a short alias like 'sonnet', or a model ID starting with 'claude-' or 'codex-')"


def _validate_human(value: Any) -> str | None:
    if not isinstance(value, bool):
        return f"'human' must be a boolean (true/false), got '{value}'"
    return None


FIELD_VALIDATORS: dict[str, Any] = {
    "status": _validate_status,
    "priority": _validate_priority,
    "effort": _validate_effort,
    "complexity": _validate_effort,
    "model": _validate_model,
    "human": _validate_human,
}


@dataclass
class Artifact:
    file_path: Path
    body: str
    metadata: dict[str, Any]


def parse_artifact(path: Path) -> Artifact:
    raw = path.read_text(encoding="utf-8")
    frontmatter_text, body = split_frontmatter(raw)
    if frontmatter_text is None:
        raise ValueError(f"missing or invalid frontmatter in {path}")

    metadata = parse_simple_yaml(frontmatter_text)
    if not isinstance(metadata, dict):
        raise ValueError(f"frontmatter is not a map in {path}")

    return Artifact(file_path=path, body=body, metadata=metadata)


def format_artifact(metadata: dict[str, Any], body: str) -> str:
    frontmatter = dump_simple_yaml(metadata).strip()
    return f"---\n{frontmatter}\n---\n\n{body.strip()}\n"


def write_artifact(artifact: Artifact) -> None:
    artifact.file_path.write_text(format_artifact(artifact.metadata, artifact.body), encoding="utf-8")


def _glob_md_dir(base: Path, results: list[Path]) -> None:
    """Glob *.md files from a directory, excluding .archive, appending to results."""
    if not base.exists():
        return
    for path in sorted(base.glob("**/*.md")):
        if ".archive" in path.relative_to(base).parts:
            continue
        results.append(path)


def artifact_glob(layout: WorkspaceLayout, project: str | None = None) -> list[Path]:
    """Glob all artifact files, optionally filtered by project.

    In multi-root mode with project=None, scans all project roots.
    Includes one-offs/ directory alongside plans/.
    """
    if layout.is_multi_root and project is None:
        # Scan all project roots
        results: list[Path] = []
        for proj_key in layout.all_project_keys():
            if proj_key is None:
                continue
            _glob_md_dir(layout.plans_dir(proj_key), results)
            _glob_md_dir(layout.one_offs_dir(proj_key), results)
        return results
    else:
        # Single root or specific project
        results: list[Path] = []
        _glob_md_dir(layout.plans_dir(project), results)
        _glob_md_dir(layout.one_offs_dir(project), results)
        return results


def collect_artifacts(layout: WorkspaceLayout, project: str | None = None) -> list[Artifact]:
    """Collect all artifacts, optionally filtered by project.

    In multi-root mode with project=None, collects from all project roots.
    """
    artifacts: list[Artifact] = []
    for path in artifact_glob(layout, project):
        artifacts.append(parse_artifact(path))
    return artifacts


def next_id(layout: WorkspaceLayout, prefix: str, project: str | None = None) -> str:
    """Generate next available ID with the given prefix.

    In multi-root mode, scans all roots to ensure global ID uniqueness.
    """
    ids: set[int] = set()
    regex = re.compile(rf"^{re.escape(prefix)}-(\d{{3}})$")

    # Always scan all artifacts in multi-root mode to ensure uniqueness
    scan_project = None if layout.is_multi_root else project
    for artifact in collect_artifacts(layout, scan_project):
        candidate = str(artifact.metadata.get("id", ""))
        match = regex.match(candidate)
        if match:
            ids.add(int(match.group(1)))

    next_num = 1
    while next_num in ids:
        next_num += 1
    return f"{prefix}-{next_num:03d}"


def next_ids(layout: WorkspaceLayout, prefix: str, count: int, project: str | None = None) -> list[str]:
    """Generate multiple sequential IDs with the given prefix.

    In multi-root mode, scans all roots to ensure global ID uniqueness.
    """
    ids: set[int] = set()
    regex = re.compile(rf"^{re.escape(prefix)}-(\d{{3}})$")

    # Always scan all artifacts in multi-root mode to ensure uniqueness
    scan_project = None if layout.is_multi_root else project
    for artifact in collect_artifacts(layout, scan_project):
        candidate = str(artifact.metadata.get("id", ""))
        match = regex.match(candidate)
        if match:
            ids.add(int(match.group(1)))
    next_num = 1
    out: list[str] = []
    while len(out) < count:
        if next_num not in ids:
            out.append(f"{prefix}-{next_num:03d}")
            ids.add(next_num)
        next_num += 1
    return out


def find_by_id(layout: WorkspaceLayout, artifact_id: str, project: str | None = None) -> Artifact | None:
    """Find artifact by ID, optionally filtered by project.

    In multi-root mode with project=None, searches all project roots.
    """
    target = artifact_id.strip()
    # In multi-root mode without a project, search all roots
    scan_project = None if layout.is_multi_root else project
    for artifact in collect_artifacts(layout, scan_project):
        if str(artifact.metadata.get("id", "")) == target:
            return artifact
    return None


def must_find_by_id(layout: WorkspaceLayout, artifact_id: str, project: str | None = None) -> Artifact:
    """Find artifact by ID, raising ValueError if not found."""
    artifact = find_by_id(layout, artifact_id, project)
    if not artifact:
        raise ValueError(f"artifact not found: {artifact_id}")
    return artifact


def find_plan_dir(layout: WorkspaceLayout, plan_id: str, project: str | None = None) -> Path:
    """Find plan directory by ID.

    In multi-root mode with project=None, searches all project roots.
    """
    pattern = f"{plan_id}-*"

    if layout.is_multi_root and project is None:
        # Search all project roots
        for proj_key in layout.all_project_keys():
            if proj_key is None:
                continue
            base = layout.plans_dir(proj_key)
            if not base.exists():
                continue
            matches = sorted(base.glob(pattern))
            if matches:
                return matches[0]
        raise ValueError(f"plan not found: {plan_id}")
    else:
        # Single root or specific project
        base = layout.plans_dir(project)
        matches = sorted(base.glob(pattern))
        if not matches:
            raise ValueError(f"plan not found: {plan_id}")
        return matches[0]


def _is_one_off_task(artifact: Artifact) -> bool:
    """True if this task lives in a one-offs/ directory (plan and chunk may be null)."""
    return "one-offs" in artifact.file_path.parts


def validate_artifact(artifact: Artifact) -> list[str]:
    issues: list[str] = []
    artifact_type = str(artifact.metadata.get("type", ""))
    required = REQUIRED_FIELDS.get(artifact_type)
    if not required:
        issues.append(f"{artifact.file_path}: unknown type '{artifact_type}'")
        return issues

    # For one-off tasks, plan and chunk are allowed to be null
    one_off = artifact_type == "task" and _is_one_off_task(artifact)
    for field in required:
        if one_off and field in ("plan", "chunk"):
            continue
        if artifact.metadata.get(field) in (None, ""):
            issues.append(f"{artifact.file_path}: missing required field '{field}'")

    # Run field-level validators for all present fields (skip None/empty optional values).
    for key, value in artifact.metadata.items():
        validator = FIELD_VALIDATORS.get(key)
        if validator is not None and value not in (None, ""):
            msg = validator(value)
            if msg:
                issues.append(f"{artifact.file_path}: {msg}")

    # Warn on unknown frontmatter fields.
    known = set(required) | set(KNOWN_FIELDS.get(artifact_type, []))
    for key in artifact.metadata:
        if key not in known:
            issues.append(f"{artifact.file_path}: unknown {artifact_type} field '{key}'")

    return issues


def _lifecycle_transition_error(current: str, action: str) -> str:
    """Human-oriented error when start/complete/cancel/retry is invalid; keep in sync with docs/LIFECYCLE.md."""
    if action == "complete":
        if current == "completed":
            return (
                "cannot complete: artifact is already completed "
                "(successful onward work marks tasks complete; no further complete is needed). "
                "See docs/LIFECYCLE.md"
            )
        if current == "canceled":
            return (
                "cannot complete: artifact is canceled (not open or in_progress). "
                "See docs/LIFECYCLE.md"
            )
        return f"cannot complete artifact in state {current!r}. See docs/LIFECYCLE.md"
    if action == "cancel":
        if current in {"completed", "canceled"}:
            return (
                f"cannot cancel: artifact is already {current} (terminal state). See docs/LIFECYCLE.md"
            )
        return f"cannot cancel artifact in state {current!r}. See docs/LIFECYCLE.md"
    if action == "retry":
        return (
            f"cannot retry: only failed tasks can be reset to open (current status is {current!r}). "
            "See docs/LIFECYCLE.md"
        )
    return f"cannot {action} artifact in state {current!r}. See docs/LIFECYCLE.md"


def transition_status(current: str, target: str) -> str:
    transitions = {
        "complete": {"open": "completed", "in_progress": "completed"},
        "cancel": {"open": "canceled", "in_progress": "canceled"},
        "retry": {"failed": "open"},
    }
    if target not in transitions:
        raise ValueError(f"unknown transition target: {target}")
    if current not in transitions[target]:
        raise ValueError(_lifecycle_transition_error(current, target))
    return transitions[target][current]


def update_artifact_status(layout: WorkspaceLayout, artifact: Artifact, status: str, project: str | None = None) -> None:
    """Update artifact status and regenerate indexes."""
    artifact.metadata["status"] = status
    artifact.metadata["updated_at"] = now_iso()
    write_artifact(artifact)
    regenerate_indexes(layout, project=project)


def artifact_project(artifact: Artifact) -> str:
    return str(artifact.metadata.get("project", "")).strip()


def resolve_project(artifact: Artifact, by_id: dict[str, Artifact]) -> str:
    """Effective project: artifact's own field, else inherited from chunk then plan."""
    direct = artifact_project(artifact)
    if direct:
        return direct
    art_type = str(artifact.metadata.get("type", ""))
    if art_type == "task":
        chunk_id = str(artifact.metadata.get("chunk", ""))
        chunk = by_id.get(chunk_id)
        if chunk:
            cp = artifact_project(chunk)
            if cp:
                return cp
        plan_id = str(artifact.metadata.get("plan", ""))
        plan = by_id.get(plan_id)
        if plan:
            return artifact_project(plan)
    elif art_type == "chunk":
        plan_id = str(artifact.metadata.get("plan", ""))
        plan = by_id.get(plan_id)
        if plan:
            return artifact_project(plan)
    return ""


def is_human_task(artifact: Artifact) -> bool:
    if str(artifact.metadata.get("type", "")) != "task":
        return False
    value = artifact.metadata.get("human", False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def summarize_complexity_remaining(artifacts: list[Artifact]) -> dict[str, int]:
    """Count open/in_progress tasks by complexity bucket (``unestimated`` = no/invalid complexity)."""
    counts = {"low": 0, "medium": 0, "high": 0, "unestimated": 0}
    for a in artifacts:
        if str(a.metadata.get("type", "")) != "task":
            continue
        if str(a.metadata.get("status", "")) not in {"open", "in_progress"}:
            continue
        e = str(a.metadata.get("complexity", "")).strip().lower()
        if e in {"low", "medium", "high"}:
            counts[e] += 1
        else:
            counts["unestimated"] += 1
    return counts


def blocking_ids(artifacts: list[Artifact]) -> set[str]:
    """IDs referenced in ``depends_on`` or legacy ``blocked_by`` (deprecated; same semantics)."""
    blockers: set[str] = set()
    for artifact in artifacts:
        status = str(artifact.metadata.get("status", ""))
        if status not in {"open", "in_progress"}:
            continue
        blockers.update(as_str_list(artifact.metadata.get("depends_on")))
        blockers.update(as_str_list(artifact.metadata.get("blocked_by")))
    return {item for item in blockers if item}


def find_dependents(artifacts: list[Artifact], task_id: str) -> list[Artifact]:
    """Tasks whose ``depends_on`` / ``blocked_by`` lists include ``task_id``."""
    tid = task_id.strip()
    out: list[Artifact] = []
    for artifact in artifacts:
        if str(artifact.metadata.get("type", "")) != "task":
            continue
        deps = as_str_list(artifact.metadata.get("depends_on")) + as_str_list(
            artifact.metadata.get("blocked_by")
        )
        if tid in deps:
            out.append(artifact)
    out.sort(key=lambda a: str(a.metadata.get("id", "")))
    return out


def create_follow_up_tasks(
    layout: WorkspaceLayout,
    parent: Artifact,
    follow_ups: list[dict[str, Any]],
    project: str | None = None,
) -> tuple[list[str], list[str]]:
    """Create tasks from executor ``follow_ups`` in the same chunk as ``parent``.

    Skips a follow-up when an **open** task with the same title already exists in the chunk.
    Returns ``(created_ids, warnings)``.
    """
    if str(parent.metadata.get("type", "")) != "task":
        raise ValueError("parent must be a task artifact")
    if not follow_ups:
        return [], []

    parent_id = str(parent.metadata.get("id", ""))
    plan_id = str(parent.metadata.get("plan", ""))
    chunk_id = str(parent.metadata.get("chunk", ""))
    parent_project = str(parent.metadata.get("project", ""))
    executor = str(parent.metadata.get("executor", "onward-exec"))

    config = load_workspace_config(layout.workspace_root)
    default_model = model_setting(config, "task_default", "sonnet")

    chunk_tasks = [
        a
        for a in collect_artifacts(layout, project)
        if str(a.metadata.get("type", "")) == "task" and str(a.metadata.get("chunk", "")) == chunk_id
    ]
    open_titles = {
        str(a.metadata.get("title", "")).strip()
        for a in chunk_tasks
        if str(a.metadata.get("status", "")) == "open"
    }

    plan_dir = find_plan_dir(layout, plan_id, project)
    tasks_dir = plan_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    warnings: list[str] = []
    body_template = load_artifact_template(layout.workspace_root, "task")

    for fu in follow_ups:
        if not isinstance(fu, dict):
            continue
        title = str(fu.get("title", "")).strip()
        desc = str(fu.get("description", "")).strip()
        if not title or not desc:
            continue
        pri = str(fu.get("priority", "medium")).strip().lower()
        if pri not in {"low", "medium", "high"}:
            pri = "medium"

        if title in open_titles:
            warnings.append(f"Follow-up skipped (duplicate open task title in chunk): {title!r}")
            continue

        task_id = next_id(layout, "TASK", project)
        now = now_iso()
        slug = slugify(title)
        metadata: dict[str, Any] = {
            "id": task_id,
            "type": "task",
            "plan": plan_id,
            "chunk": chunk_id,
            "project": parent_project,
            "title": title,
            "status": "open",
            "description": desc,
            "human": False,
            "model": default_model,
            "executor": executor,
            "depends_on": [parent_id],
            "priority": pri,
            "created_at": now,
            "updated_at": now,
        }
        target = tasks_dir / f"{task_id}-{slug}.md"
        target.write_text(format_artifact(metadata, body_template), encoding="utf-8")
        created.append(task_id)
        open_titles.add(title)

    if created:
        regenerate_indexes(layout, project=project)
    return created, warnings


def task_is_next_actionable(artifact: Artifact, status_by_id: dict[str, str]) -> bool:
    """True when ``onward work`` could run this task next (not human-only, deps satisfied).

    Only ``open`` / ``in_progress`` tasks are actionable; ``failed`` and other statuses are excluded.
    """
    if str(artifact.metadata.get("type", "")) != "task":
        return False
    status = str(artifact.metadata.get("status", ""))
    if status not in {"open", "in_progress"}:
        return False
    if is_human_task(artifact):
        return False
    all_deps = as_str_list(artifact.metadata.get("depends_on")) + as_str_list(
        artifact.metadata.get("blocked_by")
    )
    unmet = [dep for dep in all_deps if status_by_id.get(dep) != "completed"]
    if unmet:
        return False
    return True


def chunk_has_actionable_executor_task(
    artifacts: list[Artifact], chunk_id: str, status_by_id: dict[str, str]
) -> bool:
    """Chunk has at least one non-human task that ``onward work`` can run."""
    for a in artifacts:
        if str(a.metadata.get("type", "")) != "task":
            continue
        if str(a.metadata.get("chunk", "")) != chunk_id:
            continue
        if task_is_next_actionable(a, status_by_id):
            return True
    return False


def select_next_artifact(
    artifacts: list[Artifact],
    project: str | None = None,
    claimed_ids: set[str] | None = None,
) -> Artifact | None:
    _claimed = claimed_ids or set()
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
    status_by_id = {
        str(a.metadata.get("id", "")): str(a.metadata.get("status", ""))
        for a in artifacts
        if a.metadata.get("id")
    }

    ready_tasks: list[tuple[tuple[int, int, str], Artifact]] = []
    open_chunks: list[Artifact] = []
    open_plans: list[Artifact] = []

    for artifact in artifacts:
        artifact_type = str(artifact.metadata.get("type", ""))
        status = str(artifact.metadata.get("status", ""))
        aid = str(artifact.metadata.get("id", ""))

        if project and resolve_project(artifact, by_id) != project:
            continue

        if artifact_type == "task" and task_is_next_actionable(artifact, status_by_id):
            if aid in _claimed:
                continue
            chunk_status = status_by_id.get(str(artifact.metadata.get("chunk", "")), "")
            plan_status = status_by_id.get(str(artifact.metadata.get("plan", "")), "")
            rank = (
                0 if chunk_status == "in_progress" else 1,
                0 if plan_status == "in_progress" else 1,
                aid,
            )
            ready_tasks.append((rank, artifact))

        elif artifact_type == "chunk" and status == "open":
            cid = str(artifact.metadata.get("id", ""))
            if chunk_has_actionable_executor_task(artifacts, cid, status_by_id):
                open_chunks.append(artifact)
        elif artifact_type == "plan" and status == "open":
            open_plans.append(artifact)

    if ready_tasks:
        ready_tasks.sort(key=lambda item: item[0])
        return ready_tasks[0][1]
    if open_chunks:
        open_chunks.sort(key=lambda a: str(a.metadata.get("id", "")))
        return open_chunks[0]
    if open_plans:
        open_plans.sort(key=lambda a: str(a.metadata.get("id", "")))
        return open_plans[0]
    return None


def _read_index_version(layout: WorkspaceLayout, project: str | None = None) -> int:
    """Read current index version number."""
    index_path = layout.index_path(project)
    if not index_path.exists():
        return 0
    try:
        raw = index_path.read_text(encoding="utf-8")
        data = parse_simple_yaml(raw)
        if isinstance(data, dict):
            v = data.get("index_version")
            if isinstance(v, int):
                return v
    except Exception:  # noqa: BLE001
        pass
    return 0


def load_index(layout: WorkspaceLayout, project: str | None = None) -> dict[str, Any] | None:
    """Load index.yaml for a project, or None if not found.

    In multi-root mode with project=None, loads and merges indexes from all project roots.
    """
    # Multi-root mode with project=None: merge all project indexes
    if layout.is_multi_root and project is None:
        merged: dict[str, Any] = {"plans": [], "chunks": [], "tasks": []}
        for proj_key in layout.all_project_keys():
            if proj_key is None:
                continue
            proj_index = load_index(layout, proj_key)
            if proj_index and isinstance(proj_index, dict):
                for kind in ("plans", "chunks", "tasks"):
                    if kind in proj_index and isinstance(proj_index[kind], list):
                        merged[kind].extend(proj_index[kind])
        # Return None if no data was collected
        if not any(merged.get(k) for k in ("plans", "chunks", "tasks")):
            return None
        return merged

    # Single-root or specific project
    index_path = layout.index_path(project)
    if not index_path.exists():
        return None
    try:
        data = parse_simple_yaml(index_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def index_is_fresh(layout: WorkspaceLayout, index: dict[str, Any] | None = None, project: str | None = None) -> bool:
    """True when ``index.yaml`` is at least as new as every plan artifact file.

    In multi-root mode with project=None, all project indexes must be fresh.
    """
    # Multi-root mode with project=None: all project indexes must be fresh
    if layout.is_multi_root and project is None:
        for proj_key in layout.all_project_keys():
            if proj_key is None:
                continue
            if not index_is_fresh(layout, None, proj_key):
                return False
        return True

    # Single-root or specific project
    index_path = layout.index_path(project)
    if not index_path.exists():
        return False
    if index is None:
        index = load_index(layout, project)
    if not index:
        return False
    idx_mtime = index_path.stat().st_mtime
    plans_root = layout.plans_dir(project)
    if not plans_root.exists():
        return True
    newest = 0.0
    for path in plans_root.rglob("*.md"):
        if ".archive" in path.parts:
            continue
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    return idx_mtime >= newest


def _artifact_from_index_row(kind: str, row: dict[str, Any], layout: WorkspaceLayout) -> Artifact:
    """Build Artifact from index row using workspace-relative path."""
    path = layout.workspace_root / Path(str(row.get("path", "")))
    meta: dict[str, Any] = {
        "id": row.get("id"),
        "type": kind,
        "title": row.get("title"),
        "status": row.get("status"),
        "updated_at": row.get("updated_at") or "",
    }
    if kind == "plan":
        meta["project"] = row.get("project") or ""
    elif kind == "chunk":
        meta["plan"] = row.get("plan")
        meta["project"] = row.get("project") or ""
        meta["depends_on"] = row.get("depends_on") or []
        ef = row.get("estimated_files")
        if isinstance(ef, int):
            meta["estimated_files"] = ef
        complexity = row.get("complexity")
        if complexity:
            meta["complexity"] = complexity
    elif kind == "task":
        meta["plan"] = row.get("plan")
        meta["chunk"] = row.get("chunk")
        meta["project"] = row.get("project") or ""
        meta["depends_on"] = row.get("depends_on") or []
        meta["blocked_by"] = row.get("blocked_by") or []
        meta["human"] = bool(row.get("human", False))
        complexity = row.get("complexity")
        if complexity:
            meta["complexity"] = complexity
    return Artifact(file_path=path, body="", metadata=meta)


def artifacts_from_index(index: dict[str, Any], layout: WorkspaceLayout) -> list[Artifact]:
    """Build artifact list from index data."""
    out: list[Artifact] = []
    for row in index.get("plans") or []:
        if isinstance(row, dict) and row.get("id"):
            out.append(_artifact_from_index_row("plan", row, layout))
    for row in index.get("chunks") or []:
        if isinstance(row, dict) and row.get("id"):
            out.append(_artifact_from_index_row("chunk", row, layout))
    for row in index.get("tasks") or []:
        if isinstance(row, dict) and row.get("id"):
            out.append(_artifact_from_index_row("task", row, layout))
    return out


def collect_artifacts_fast(layout: WorkspaceLayout, project: str | None = None) -> list[Artifact] | None:
    """Try to collect artifacts from index if fresh, else return None."""
    index = load_index(layout, project)
    if not index or not index_is_fresh(layout, index, project):
        return None
    return artifacts_from_index(index, layout)


def artifacts_from_index_or_collect(layout: WorkspaceLayout, project: str | None = None) -> list[Artifact]:
    """Collect artifacts using fast index path if possible, else full glob."""
    fast = collect_artifacts_fast(layout, project)
    if fast is not None:
        return fast
    return collect_artifacts(layout, project)


def list_from_index(
    layout: WorkspaceLayout,
    *,
    type_filter: str = "all",
    project_filter: str = "",
    project: str | None = None,
    blocking: bool = False,
    human_only: bool = False,
) -> list[dict[str, str]] | None:
    """Return tabular rows from a fresh index, or None to signal fallback to full scan."""
    index = load_index(layout, project)
    if not index or not index_is_fresh(layout, index, project):
        return None
    project_filter = project_filter.strip()
    artifacts_full = artifacts_from_index(index, layout)
    blocker_ids = blocking_ids(artifacts_full) if blocking else set()

    by_id = {str(a.metadata.get("id", "")): a for a in artifacts_full if a.metadata.get("id")}

    rows: list[dict[str, str]] = []

    def consider(kind: str, row: dict[str, Any]) -> None:
        if not isinstance(row, dict) or not row.get("id"):
            return
        aid = str(row["id"])
        pseudo = _artifact_from_index_row(kind, row, layout)
        if type_filter != "all" and kind != type_filter:
            return
        if project_filter and resolve_project(pseudo, by_id) != project_filter:
            return
        if blocking and aid not in blocker_ids:
            return
        if human_only and (kind != "task" or not is_human_task(pseudo)):
            return
        rows.append(
            {
                "id": aid,
                "type": kind,
                "status": str(row.get("status", "")),
                "project": resolve_project(pseudo, by_id),
                "human": "true" if kind == "task" and is_human_task(pseudo) else "false",
                "title": str(row.get("title", "")),
                "path": str(row.get("path", "")),
            }
        )

    if type_filter in ("all", "plan"):
        for row in index.get("plans") or []:
            consider("plan", row)
    if type_filter in ("all", "chunk"):
        for row in index.get("chunks") or []:
            consider("chunk", row)
    if type_filter in ("all", "task"):
        for row in index.get("tasks") or []:
            consider("task", row)

    rows.sort(key=lambda r: (r["type"], r["id"]))
    return rows


def regenerate_indexes(layout: WorkspaceLayout, run_records: list[dict[str, Any]] | None = None, project: str | None = None) -> None:
    """Regenerate index.yaml and recent.yaml for a project.

    In multi-root mode with project=None, regenerates indexes for all projects.
    """
    if layout.is_multi_root and project is None:
        # Regenerate indexes for all projects
        for proj_key in layout.all_project_keys():
            if proj_key is None:
                continue
            regenerate_indexes(layout, run_records=run_records, project=proj_key)
        return

    index_path = layout.index_path(project)
    recent_path = layout.recent_path(project)

    plans: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []

    for artifact in collect_artifacts(layout, project):
        m = artifact.metadata
        row: dict[str, Any] = {
            "id": m.get("id"),
            "title": m.get("title"),
            "status": m.get("status"),
            "updated_at": m.get("updated_at") or "",
            "path": str(artifact.file_path.relative_to(layout.workspace_root)),
        }

        artifact_type = m.get("type")
        if artifact_type == "plan":
            row["project"] = m.get("project") or ""
            plans.append(row)
        elif artifact_type == "chunk":
            row["plan"] = m.get("plan")
            row["project"] = m.get("project") or ""
            row["depends_on"] = as_str_list(m.get("depends_on"))
            ef = m.get("estimated_files")
            if isinstance(ef, int):
                row["estimated_files"] = ef
            complexity = m.get("complexity")
            if complexity:
                row["complexity"] = str(complexity).strip()
            chunks.append(row)
        elif artifact_type == "task":
            row["plan"] = m.get("plan")
            row["chunk"] = m.get("chunk")
            row["project"] = m.get("project") or ""
            row["depends_on"] = as_str_list(m.get("depends_on"))
            bb = as_str_list(m.get("blocked_by"))
            if bb:
                row["blocked_by"] = bb
            row["human"] = is_human_task(artifact)
            complexity = m.get("complexity")
            if complexity:
                row["complexity"] = str(complexity).strip()
            tasks.append(row)

    key_fn = lambda row: (str(row.get("id", "")), str(row.get("title", "")))
    plans.sort(key=key_fn)
    chunks.sort(key=key_fn)
    tasks.sort(key=key_fn)

    runs_index: list[dict[str, Any]] = []
    if run_records is None:
        run_dir = layout.runs_dir(project)
        if run_dir.exists():
            for path in sorted(run_dir.glob("RUN-*.json")):
                try:
                    rec = read_run_json_record(path.read_text(encoding="utf-8"))
                    runs_index.append({
                        "id": rec.get("id"),
                        "target": rec.get("target"),
                        "status": rec.get("status"),
                        "started_at": rec.get("started_at"),
                    })
                except Exception:  # noqa: BLE001
                    continue
    else:
        for rec in run_records:
            runs_index.append({
                "id": rec.get("id"),
                "target": rec.get("target"),
                "status": rec.get("status"),
                "started_at": rec.get("started_at"),
            })

    index_payload = {
        "generated_at": now_iso(),
        "index_version": _read_index_version(layout, project) + 1,
        "plans": plans,
        "chunks": chunks,
        "tasks": tasks,
        "runs": runs_index,
    }
    index_path.write_text(dump_simple_yaml(index_payload), encoding="utf-8")

    completed_rows = [
        *[p for p in plans if p.get("status") == "completed"],
        *[c for c in chunks if c.get("status") == "completed"],
        *[t for t in tasks if t.get("status") == "completed"],
    ]
    recent_payload = {
        "generated_at": now_iso(),
        "completed": completed_rows,
    }
    recent_path.write_text(dump_simple_yaml(recent_payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


def _notes_path(layout: WorkspaceLayout, artifact_id: str, project: str | None = None) -> Path:
    """Get notes file path for an artifact."""
    return layout.notes_dir(project) / f"{artifact_id}.md"


def read_notes(layout: WorkspaceLayout, artifact_id: str, project: str | None = None) -> str:
    """Read notes for an artifact, returning empty string if not found."""
    path = _notes_path(layout, artifact_id, project)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def append_note(layout: WorkspaceLayout, artifact: Artifact, message: str, project: str | None = None) -> Path:
    """Append a timestamped note to an artifact's notes file."""
    artifact_id = str(artifact.metadata.get("id", ""))
    path = _notes_path(layout, artifact_id, project)
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = now_iso()
    entry = f"## {timestamp}\n\n{message.strip()}\n\n"

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        path.write_text(existing + entry, encoding="utf-8")
    else:
        path.write_text(entry, encoding="utf-8")

    if not artifact.metadata.get("has_notes"):
        artifact.metadata["has_notes"] = True
        artifact.metadata["updated_at"] = now_iso()
        write_artifact(artifact)
        regenerate_indexes(layout, project=project)

    return path


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def report_rows(
    artifacts: list[Artifact],
    layout: WorkspaceLayout,
    status: str | None = None,
    project: str | None = None,
    claimed_ids: set[str] | None = None,
) -> list[str]:
    """Return tab-separated artifact rows, excluding tasks whose ID is in ``claimed_ids``."""
    _claimed = claimed_ids or set()
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
    rows: list[str] = []
    for artifact in artifacts:
        if status and str(artifact.metadata.get("status", "")) != status:
            continue
        if project and resolve_project(artifact, by_id) != project:
            continue
        aid = str(artifact.metadata.get("id", ""))
        if str(artifact.metadata.get("type", "")) == "task" and aid in _claimed:
            continue
        rows.append(
            "\t".join(
                [
                    aid,
                    str(artifact.metadata.get("type", "")),
                    str(artifact.metadata.get("status", "")),
                    str(artifact.metadata.get("title", "")),
                    str(artifact.file_path.relative_to(layout.workspace_root)),
                ]
            )
        )
    return sorted(rows)


def claimed_rows(
    artifacts: list[Artifact],
    layout: WorkspaceLayout,
    claimed_ids: set[str],
    project: str | None = None,
) -> list[str]:
    """Return tab-separated rows for tasks currently claimed by an active chunk/plan run."""
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
    rows: list[str] = []
    for artifact in artifacts:
        if str(artifact.metadata.get("type", "")) != "task":
            continue
        aid = str(artifact.metadata.get("id", ""))
        if aid not in claimed_ids:
            continue
        if project and resolve_project(artifact, by_id) != project:
            continue
        rows.append(
            "\t".join(
                [
                    aid,
                    "task",
                    str(artifact.metadata.get("status", "")),
                    str(artifact.metadata.get("title", "")),
                    str(artifact.file_path.relative_to(layout.workspace_root)),
                ]
            )
        )
    return sorted(rows)


def _plan_visible_for_project_filter(
    plan: Artifact,
    artifacts: list[Artifact],
    project: str,
    by_id: dict[str, Artifact],
) -> bool:
    if resolve_project(plan, by_id) == project:
        return True
    pid = str(plan.metadata.get("id", ""))
    for c in artifacts:
        if str(c.metadata.get("type", "")) != "chunk" or str(c.metadata.get("plan", "")) != pid:
            continue
        if resolve_project(c, by_id) == project:
            return True
        cid = str(c.metadata.get("id", ""))
        for t in artifacts:
            if str(t.metadata.get("type", "")) != "task" or str(t.metadata.get("chunk", "")) != cid:
                continue
            if resolve_project(t, by_id) == project:
                return True
    return False


def render_active_work_tree_lines(
    artifacts: list[Artifact],
    layout: WorkspaceLayout,
    project: str | None = None,
    color_enabled: bool = False,
) -> list[str]:
    """Lines for ``onward tree`` / report: non-terminal plans with active descendants.

    Includes ``open`` and ``in_progress`` plans, but only if they have at least one
    active chunk or task beneath them.  Terminal chunks/tasks (``completed`` / ``canceled``)
    are omitted so the view matches *active* work.
    """
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
    active_plan_status = frozenset({"open", "in_progress"})
    candidate_plans = [
        a
        for a in artifacts
        if str(a.metadata.get("type", "")) == "plan"
        and str(a.metadata.get("status", "")) in active_plan_status
        and (not project or _plan_visible_for_project_filter(a, artifacts, project, by_id))
    ]
    candidate_plans.sort(key=lambda a: str(a.metadata.get("id", "")))
    if not candidate_plans:
        return []

    chunks = [a for a in artifacts if str(a.metadata.get("type", "")) == "chunk"]
    tasks = [a for a in artifacts if str(a.metadata.get("type", "")) == "task"]
    active_chunk_status = frozenset({"open", "in_progress"})
    active_task_status = frozenset({"open", "in_progress", "failed"})
    lines: list[str] = []
    for plan in candidate_plans:
        plan_id = str(plan.metadata.get("id", ""))
        plan_chunks = [
            c
            for c in chunks
            if str(c.metadata.get("plan", "")) == plan_id
            and str(c.metadata.get("status", "")) in active_chunk_status
        ]
        plan_chunks.sort(key=lambda a: str(a.metadata.get("id", "")))

        # Also check for orphan tasks directly under the plan
        plan_direct_tasks = [
            t
            for t in tasks
            if str(t.metadata.get("plan", "")) == plan_id
            and not str(t.metadata.get("chunk", "")).strip()
            and str(t.metadata.get("status", "")) in active_task_status
        ]

        if not plan_chunks and not plan_direct_tasks:
            continue

        p_status = str(plan.metadata.get("status", ""))
        p_status_text = colorize(p_status, status_color(p_status), color_enabled)
        lines.append(f"{plan.metadata.get('id')} [{p_status_text}] {plan.metadata.get('title')}")
        for chunk in plan_chunks:
            status = str(chunk.metadata.get("status", ""))
            status_text = colorize(status, status_color(status), color_enabled)
            lines.append(f"  |- {chunk.metadata.get('id')} [{status_text}] {chunk.metadata.get('title')}")
            chunk_tasks = [
                t
                for t in tasks
                if str(t.metadata.get("chunk", "")) == str(chunk.metadata.get("id", ""))
                and str(t.metadata.get("status", "")) in active_task_status
            ]
            chunk_tasks.sort(key=lambda a: str(a.metadata.get("id", "")))
            for task in chunk_tasks:
                t_status = str(task.metadata.get("status", ""))
                t_status_text = colorize(t_status, status_color(t_status), color_enabled)
                marker = "H" if is_human_task(task) else "A"
                eff = str(task.metadata.get("complexity", "")).strip()
                eff_s = f" [{eff}]" if eff else ""
                lines.append(
                    f"  |  |- {task.metadata.get('id')} [{t_status_text}] ({marker}) {task.metadata.get('title')}{eff_s}"
                )
    return lines
