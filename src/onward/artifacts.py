from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onward.util import (
    _as_str_list,
    _colorize,
    _dump_simple_yaml,
    _now_iso,
    _parse_simple_yaml,
    _slugify,
    _split_frontmatter,
    _status_color,
)

REQUIRED_FIELDS = {
    "plan": ["id", "type", "title", "status", "created_at", "updated_at"],
    "chunk": ["id", "type", "plan", "title", "status", "created_at", "updated_at"],
    "task": ["id", "type", "plan", "chunk", "title", "status", "created_at", "updated_at"],
}


@dataclass
class Artifact:
    file_path: Path
    body: str
    metadata: dict[str, Any]


def _parse_artifact(path: Path) -> Artifact:
    raw = path.read_text(encoding="utf-8")
    frontmatter_text, body = _split_frontmatter(raw)
    if frontmatter_text is None:
        raise ValueError(f"missing or invalid frontmatter in {path}")

    metadata = _parse_simple_yaml(frontmatter_text)
    if not isinstance(metadata, dict):
        raise ValueError(f"frontmatter is not a map in {path}")

    return Artifact(file_path=path, body=body, metadata=metadata)


def _format_artifact(metadata: dict[str, Any], body: str) -> str:
    frontmatter = _dump_simple_yaml(metadata).strip()
    return f"---\n{frontmatter}\n---\n\n{body.strip()}\n"


def _write_artifact(artifact: Artifact) -> None:
    artifact.file_path.write_text(_format_artifact(artifact.metadata, artifact.body), encoding="utf-8")


def _artifact_glob(root: Path) -> list[Path]:
    base = root / ".onward/plans"
    if not base.exists():
        return []
    results: list[Path] = []
    for path in sorted(base.glob("**/*.md")):
        if ".archive" in path.relative_to(base).parts:
            continue
        results.append(path)
    return results


def _collect_artifacts(root: Path) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for path in _artifact_glob(root):
        artifacts.append(_parse_artifact(path))
    return artifacts


def _next_id(root: Path, prefix: str) -> str:
    ids: set[int] = set()
    regex = re.compile(rf"^{re.escape(prefix)}-(\d{{3}})$")

    for artifact in _collect_artifacts(root):
        candidate = str(artifact.metadata.get("id", ""))
        match = regex.match(candidate)
        if match:
            ids.add(int(match.group(1)))

    next_num = 1
    while next_num in ids:
        next_num += 1
    return f"{prefix}-{next_num:03d}"


def _next_ids(root: Path, prefix: str, count: int) -> list[str]:
    ids: set[int] = set()
    regex = re.compile(rf"^{re.escape(prefix)}-(\d{{3}})$")
    for artifact in _collect_artifacts(root):
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


def _find_by_id(root: Path, artifact_id: str) -> Artifact | None:
    target = artifact_id.strip()
    for artifact in _collect_artifacts(root):
        if str(artifact.metadata.get("id", "")) == target:
            return artifact
    return None


def _must_find_by_id(root: Path, artifact_id: str) -> Artifact:
    artifact = _find_by_id(root, artifact_id)
    if not artifact:
        raise ValueError(f"artifact not found: {artifact_id}")
    return artifact


def _find_plan_dir(root: Path, plan_id: str) -> Path:
    base = root / ".onward/plans"
    pattern = f"{plan_id}-*"
    matches = sorted(base.glob(pattern))
    if not matches:
        raise ValueError(f"plan not found: {plan_id}")
    return matches[0]


def _validate_artifact(artifact: Artifact) -> list[str]:
    issues: list[str] = []
    artifact_type = str(artifact.metadata.get("type", ""))
    fields = REQUIRED_FIELDS.get(artifact_type)
    if not fields:
        issues.append(f"{artifact.file_path}: unknown type '{artifact_type}'")
        return issues

    for field in fields:
        if artifact.metadata.get(field) in (None, ""):
            issues.append(f"{artifact.file_path}: missing required field '{field}'")

    status = str(artifact.metadata.get("status", ""))
    if status and status not in {"open", "in_progress", "completed", "canceled"}:
        issues.append(f"{artifact.file_path}: invalid status '{status}'")

    return issues


def _transition_status(current: str, target: str) -> str:
    transitions = {
        "start": {"open": "in_progress"},
        "complete": {"open": "completed", "in_progress": "completed"},
        "cancel": {"open": "canceled", "in_progress": "canceled"},
    }
    if target not in transitions:
        raise ValueError(f"unknown transition target: {target}")
    if current not in transitions[target]:
        raise ValueError(f"cannot {target} artifact in state '{current}'")
    return transitions[target][current]


def _update_artifact_status(root: Path, artifact: Artifact, status: str) -> None:
    artifact.metadata["status"] = status
    artifact.metadata["updated_at"] = _now_iso()
    _write_artifact(artifact)
    _regenerate_indexes(root)


def _artifact_project(artifact: Artifact) -> str:
    return str(artifact.metadata.get("project", "")).strip()


def _is_human_task(artifact: Artifact) -> bool:
    if str(artifact.metadata.get("type", "")) != "task":
        return False
    value = artifact.metadata.get("human", False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _blocking_ids(artifacts: list[Artifact]) -> set[str]:
    blockers: set[str] = set()
    for artifact in artifacts:
        status = str(artifact.metadata.get("status", ""))
        if status not in {"open", "in_progress"}:
            continue
        blockers.update(_as_str_list(artifact.metadata.get("depends_on")))
        blockers.update(_as_str_list(artifact.metadata.get("blocked_by")))
    return {item for item in blockers if item}


def _select_next_artifact(artifacts: list[Artifact], project: str | None = None) -> Artifact | None:
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

        if project and _artifact_project(artifact) != project:
            continue

        if artifact_type == "task" and status == "open":
            depends_on = _as_str_list(artifact.metadata.get("depends_on"))
            blocked_by = _as_str_list(artifact.metadata.get("blocked_by"))
            if blocked_by:
                continue
            unmet = [dep for dep in depends_on if status_by_id.get(dep) != "completed"]
            if unmet:
                continue

            chunk_status = status_by_id.get(str(artifact.metadata.get("chunk", "")), "")
            plan_status = status_by_id.get(str(artifact.metadata.get("plan", "")), "")
            rank = (
                0 if chunk_status == "in_progress" else 1,
                0 if plan_status == "in_progress" else 1,
                str(artifact.metadata.get("id", "")),
            )
            ready_tasks.append((rank, artifact))

        elif artifact_type == "chunk" and status == "open":
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


def _regenerate_indexes(root: Path) -> None:
    index_path = root / ".onward/plans/index.yaml"
    recent_path = root / ".onward/plans/recent.yaml"

    plans: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []

    for artifact in _collect_artifacts(root):
        m = artifact.metadata
        row = {
            "id": m.get("id"),
            "title": m.get("title"),
            "status": m.get("status"),
            "path": str(artifact.file_path.relative_to(root)),
        }

        artifact_type = m.get("type")
        if artifact_type == "plan":
            plans.append(row)
        elif artifact_type == "chunk":
            row["plan"] = m.get("plan")
            chunks.append(row)
        elif artifact_type == "task":
            row["plan"] = m.get("plan")
            row["chunk"] = m.get("chunk")
            tasks.append(row)

    key_fn = lambda row: (str(row.get("id", "")), str(row.get("title", "")))
    plans.sort(key=key_fn)
    chunks.sort(key=key_fn)
    tasks.sort(key=key_fn)

    index_payload = {
        "generated_at": _now_iso(),
        "plans": plans,
        "chunks": chunks,
        "tasks": tasks,
        "runs": [],
    }
    index_path.write_text(_dump_simple_yaml(index_payload), encoding="utf-8")

    completed_rows = [
        *[p for p in plans if p.get("status") == "completed"],
        *[c for c in chunks if c.get("status") == "completed"],
        *[t for t in tasks if t.get("status") == "completed"],
    ]
    recent_payload = {
        "generated_at": _now_iso(),
        "completed": completed_rows,
    }
    recent_path.write_text(_dump_simple_yaml(recent_payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


def _notes_path(root: Path, artifact_id: str) -> Path:
    return root / ".onward/notes" / f"{artifact_id}.md"


def _read_notes(root: Path, artifact_id: str) -> str:
    path = _notes_path(root, artifact_id)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _append_note(root: Path, artifact: Artifact, message: str) -> Path:
    artifact_id = str(artifact.metadata.get("id", ""))
    path = _notes_path(root, artifact_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = _now_iso()
    entry = f"## {timestamp}\n\n{message.strip()}\n\n"

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        path.write_text(existing + entry, encoding="utf-8")
    else:
        path.write_text(entry, encoding="utf-8")

    if not artifact.metadata.get("has_notes"):
        artifact.metadata["has_notes"] = True
        artifact.metadata["updated_at"] = _now_iso()
        _write_artifact(artifact)
        _regenerate_indexes(root)

    return path


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _report_rows(artifacts: list[Artifact], root: Path, status: str | None = None, project: str | None = None) -> list[str]:
    rows: list[str] = []
    for artifact in artifacts:
        if status and str(artifact.metadata.get("status", "")) != status:
            continue
        if project and _artifact_project(artifact) != project:
            continue
        rows.append(
            "\t".join(
                [
                    str(artifact.metadata.get("id", "")),
                    str(artifact.metadata.get("type", "")),
                    str(artifact.metadata.get("status", "")),
                    str(artifact.metadata.get("title", "")),
                    str(artifact.file_path.relative_to(root)),
                ]
            )
        )
    return sorted(rows)


def _render_open_tree_lines(
    artifacts: list[Artifact],
    root: Path,
    project: str | None = None,
    color_enabled: bool = False,
) -> list[str]:
    plans = [
        a
        for a in artifacts
        if str(a.metadata.get("type", "")) == "plan"
        and str(a.metadata.get("status", "")) == "open"
        and (not project or _artifact_project(a) == project)
    ]
    plans.sort(key=lambda a: str(a.metadata.get("id", "")))
    if not plans:
        return []

    chunks = [a for a in artifacts if str(a.metadata.get("type", "")) == "chunk"]
    tasks = [a for a in artifacts if str(a.metadata.get("type", "")) == "task"]
    lines: list[str] = []
    for plan in plans:
        lines.append(f"{plan.metadata.get('id')} {plan.metadata.get('title')}")
        plan_chunks = [c for c in chunks if str(c.metadata.get("plan", "")) == str(plan.metadata.get("id", ""))]
        plan_chunks.sort(key=lambda a: str(a.metadata.get("id", "")))
        for chunk in plan_chunks:
            status = str(chunk.metadata.get("status", ""))
            status_text = _colorize(status, _status_color(status), color_enabled)
            lines.append(f"  |- {chunk.metadata.get('id')} [{status_text}] {chunk.metadata.get('title')}")
            chunk_tasks = [t for t in tasks if str(t.metadata.get('chunk', '')) == str(chunk.metadata.get("id", ""))]
            chunk_tasks.sort(key=lambda a: str(a.metadata.get("id", "")))
            for task in chunk_tasks:
                t_status = str(task.metadata.get("status", ""))
                t_status_text = _colorize(t_status, _status_color(t_status), color_enabled)
                marker = "H" if _is_human_task(task) else "A"
                lines.append(f"  |  |- {task.metadata.get('id')} [{t_status_text}] ({marker}) {task.metadata.get('title')}")
    return lines
