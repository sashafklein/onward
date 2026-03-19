from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_DIRECTORIES = [
    ".train/plans",
    ".train/plans/.archive",
    ".train/templates",
    ".train/hooks",
    ".train/sync",
    ".train/runs",
]

DEFAULT_FILES = {
    ".train.config.yaml": """version: 1

paths:
  plans_dir: .train/plans
  runtime_dir: .train

sync:
  mode: local
  branch: train
  repo: null
  worktree_path: .train/sync

ralph:
  command: ralph
  args: []
  enabled: true

models:
  default: gpt-5
  task_default: gpt-5-mini
  split_default: gpt-5
  review_default: gpt-5

work:
  sequential_by_default: true
  create_worktree: true
  worktree_root: .worktrees
  base_branch: main

hooks:
  pre_task_shell: []
  post_task_shell: []
  pre_task_markdown: null
  post_task_markdown: .train/hooks/post-task.md
  post_chunk_markdown: .train/hooks/post-chunk.md
""",
    ".train/templates/plan.md": """# Summary

# Problem

# Goals

# Non-goals

# Context

# Proposed approach

# Risks

# Chunking strategy

# Acceptance criteria

# Notes
""",
    ".train/templates/chunk.md": """# Summary

# Scope

# Out of scope

# Dependencies

# Expected files/systems involved

# Completion criteria

# Notes
""",
    ".train/templates/task.md": """# Context

# Scope

# Out of scope

# Files to inspect

# Implementation notes

# Acceptance criteria

# Handoff notes
""",
    ".train/templates/run.md": """# Execution summary

# Inputs

# Output

# Follow-up
""",
    ".train/hooks/post-task.md": """---
id: HOOK-post-task
type: hook
trigger: task.completed
model: gpt-5
executor: ralph
scope: repo
---

# Purpose
Summarize what changed and propose next tasks.

# Inputs
- Completed task
- Run output

# Instructions
1. Confirm acceptance criteria status.
2. Note key files touched.
3. Propose follow-up tasks if needed.

# Required output
- Short completion summary
- Follow-up list (if any)
""",
    ".train/hooks/post-chunk.md": """---
id: HOOK-post-chunk
type: hook
trigger: chunk.completed
model: gpt-5
executor: ralph
scope: repo
---

# Purpose
Capture chunk-level completion and recommend plan updates.

# Inputs
- Completed chunk
- Child task outcomes

# Instructions
1. Verify the chunk completion criteria.
2. Summarize major outputs and known risks.
3. Suggest next chunk ordering.

# Required output
- Chunk completion status
- Risks and recommended next actions
""",
    ".train/plans/index.yaml": """generated_at: null
plans: []
chunks: []
tasks: []
runs: []
""",
    ".train/plans/recent.yaml": """generated_at: null
completed: []
""",
    ".train/ongoing.json": """{
  "version": 1,
  "updated_at": null,
  "active_runs": []
}
""",
}

GITIGNORE_LINES = [
    ".train/plans/.archive/",
    ".train/runs/",
    ".train/ongoing.json",
    ".dogfood/",
]

REQUIRED_PATHS = [
    ".train.config.yaml",
    ".train/templates/plan.md",
    ".train/templates/chunk.md",
    ".train/templates/task.md",
    ".train/templates/run.md",
    ".train/plans/index.yaml",
    ".train/plans/recent.yaml",
]

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


def _write_file(path: Path, content: str, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _update_gitignore(root: Path) -> bool:
    gitignore = root / ".gitignore"
    existing = []
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8").splitlines()

    changed = False
    lines = existing.copy()
    for entry in GITIGNORE_LINES:
        if entry not in lines:
            lines.append(entry)
            changed = True

    if not changed:
        return False

    gitignore.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "item"


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value in {"null", "~"}:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    i = 0
    result: dict[str, Any] = {}

    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue

        if line.startswith("  "):
            raise ValueError(f"unexpected indentation near: {line}")

        if ":" not in line:
            raise ValueError(f"invalid yaml line: {line}")

        key, remainder = line.split(":", 1)
        key = key.strip()
        remainder = remainder.strip()

        if remainder:
            result[key] = _parse_scalar(remainder)
            i += 1
            continue

        j = i + 1
        list_items: list[Any] = []
        nested_lines: list[str] = []

        while j < len(lines):
            child = lines[j]
            if not child.strip():
                j += 1
                continue
            if not child.startswith("  "):
                break

            if child.startswith("  - "):
                list_items.append(_parse_scalar(child[4:].strip()))
            else:
                nested_lines.append(child[2:])
            j += 1

        if list_items and nested_lines:
            raise ValueError(f"mixed nested yaml not supported for key: {key}")

        if list_items:
            result[key] = list_items
        elif nested_lines:
            result[key] = _parse_simple_yaml("\n".join(nested_lines))
        else:
            result[key] = ""

        i = j

    return result


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def _dump_simple_yaml_lines(data: Any, indent: int = 0) -> list[str]:
    pad = " " * indent

    if isinstance(data, dict):
        out: list[str] = []
        for key, value in data.items():
            if isinstance(value, dict):
                if not value:
                    out.append(f"{pad}{key}: {{}}")
                    continue
                out.append(f"{pad}{key}:")
                out.extend(_dump_simple_yaml_lines(value, indent + 2))
            elif isinstance(value, list):
                if not value:
                    out.append(f"{pad}{key}: []")
                    continue
                out.append(f"{pad}{key}:")
                out.extend(_dump_simple_yaml_lines(value, indent + 2))
            else:
                out.append(f"{pad}{key}: {_format_scalar(value)}")
        return out

    if isinstance(data, list):
        out = []
        for item in data:
            if isinstance(item, (dict, list)):
                out.append(f"{pad}-")
                out.extend(_dump_simple_yaml_lines(item, indent + 2))
            else:
                out.append(f"{pad}- {_format_scalar(item)}")
        return out

    return [f"{pad}{_format_scalar(data)}"]


def _dump_simple_yaml(data: dict[str, Any]) -> str:
    return "\n".join(_dump_simple_yaml_lines(data)) + "\n"


def _split_frontmatter(raw: str) -> tuple[str | None, str]:
    if not raw.startswith("---\n"):
        return None, raw
    remainder = raw[4:]
    marker = "\n---\n"
    idx = remainder.find(marker)
    if idx < 0:
        return None, raw
    frontmatter = remainder[:idx]
    body = remainder[idx + len(marker) :]
    return frontmatter, body


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
    base = root / ".train/plans"
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


def _load_template(root: Path, artifact_type: str) -> str:
    return (root / f".train/templates/{artifact_type}.md").read_text(encoding="utf-8")


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
    base = root / ".train/plans"
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


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [raw]


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
    index_path = root / ".train/plans/index.yaml"
    recent_path = root / ".train/plans/recent.yaml"

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


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()

    for rel_path in DEFAULT_DIRECTORIES:
        (root / rel_path).mkdir(parents=True, exist_ok=True)

    created = 0
    for rel_path, content in DEFAULT_FILES.items():
        wrote = _write_file(root / rel_path, content, force=args.force)
        if wrote:
            created += 1

    gitignore_updated = _update_gitignore(root)
    _regenerate_indexes(root)

    print(f"Initialized Trains workspace in {root}")
    print(f"Created/updated files: {created}")
    if gitignore_updated:
        print("Updated .gitignore")

    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    issues: list[str] = []

    for rel_path in REQUIRED_PATHS:
        path = root / rel_path
        if not path.exists():
            issues.append(f"missing required file: {rel_path}")

    ongoing_path = root / ".train/ongoing.json"
    if ongoing_path.exists():
        try:
            json.loads(ongoing_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(f"invalid json in .train/ongoing.json: {exc}")

    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        issues.append("missing .gitignore")
    else:
        lines = set(gitignore_path.read_text(encoding="utf-8").splitlines())
        for entry in GITIGNORE_LINES:
            if entry not in lines:
                issues.append(f"missing .gitignore entry: {entry}")

    seen_ids: set[str] = set()
    for path in _artifact_glob(root):
        try:
            artifact = _parse_artifact(path)
        except Exception as exc:  # noqa: BLE001
            issues.append(str(exc))
            continue

        artifact_issues = _validate_artifact(artifact)
        issues.extend(artifact_issues)

        artifact_id = str(artifact.metadata.get("id", ""))
        if artifact_id:
            if artifact_id in seen_ids:
                issues.append(f"duplicate id found: {artifact_id}")
            seen_ids.add(artifact_id)

    if issues:
        print("Doctor found issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Doctor check passed")
    return 0


def cmd_new_plan(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    plan_id = _next_id(root, "PLAN")
    now = _now_iso()
    slug = _slugify(args.title)

    plan_dir = root / ".train/plans" / f"{plan_id}-{slug}"
    plan_dir.mkdir(parents=True, exist_ok=False)
    (plan_dir / "chunks").mkdir(parents=True, exist_ok=True)
    (plan_dir / "tasks").mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": plan_id,
        "type": "plan",
        "project": args.project or "",
        "title": args.title,
        "status": "open",
        "description": args.description or "",
        "priority": args.priority,
        "model": args.model,
        "created_at": now,
        "updated_at": now,
    }

    body = _load_template(root, "plan")
    target = plan_dir / "plan.md"
    target.write_text(_format_artifact(metadata, body), encoding="utf-8")

    _regenerate_indexes(root)
    print(f"Created {plan_id} at {target.relative_to(root)}")
    return 0


def cmd_new_chunk(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    plan_id = args.plan_id

    plan_dir = _find_plan_dir(root, plan_id)
    chunk_id = _next_id(root, "CHUNK")
    now = _now_iso()
    slug = _slugify(args.title)

    metadata = {
        "id": chunk_id,
        "type": "chunk",
        "plan": plan_id,
        "project": args.project or "",
        "title": args.title,
        "status": "open",
        "description": args.description or "",
        "priority": args.priority,
        "model": args.model,
        "created_at": now,
        "updated_at": now,
    }

    body = _load_template(root, "chunk")
    target = plan_dir / "chunks" / f"{chunk_id}-{slug}.md"
    target.write_text(_format_artifact(metadata, body), encoding="utf-8")

    _regenerate_indexes(root)
    print(f"Created {chunk_id} at {target.relative_to(root)}")
    return 0


def cmd_new_task(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    chunk = _find_by_id(root, args.chunk_id)
    if not chunk:
        raise ValueError(f"chunk not found: {args.chunk_id}")
    if chunk.metadata.get("type") != "chunk":
        raise ValueError(f"{args.chunk_id} is not a chunk")

    plan_id = str(chunk.metadata["plan"])
    chunk_id = str(chunk.metadata["id"])
    task_id = _next_id(root, "TASK")
    now = _now_iso()
    slug = _slugify(args.title)

    plan_dir = _find_plan_dir(root, plan_id)
    metadata = {
        "id": task_id,
        "type": "task",
        "plan": plan_id,
        "chunk": chunk_id,
        "project": args.project or "",
        "title": args.title,
        "status": "open",
        "description": args.description or "",
        "human": bool(args.human),
        "model": args.model,
        "executor": "ralph",
        "depends_on": [],
        "blocked_by": [],
        "files": [],
        "acceptance": [],
        "created_at": now,
        "updated_at": now,
    }

    body = _load_template(root, "task")
    target = plan_dir / "tasks" / f"{task_id}-{slug}.md"
    target.write_text(_format_artifact(metadata, body), encoding="utf-8")

    _regenerate_indexes(root)
    print(f"Created {task_id} at {target.relative_to(root)}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifact_type = args.type
    project_filter = (args.project or "").strip()
    blockers_only = bool(args.blocking)
    human_only = bool(args.human)
    artifacts = _collect_artifacts(root)
    blocker_ids = _blocking_ids(artifacts) if blockers_only else set()

    rows: list[dict[str, str]] = []
    for artifact in artifacts:
        m = artifact.metadata
        row_type = str(m.get("type", ""))
        if artifact_type != "all" and row_type != artifact_type:
            continue
        if project_filter and _artifact_project(artifact) != project_filter:
            continue
        if blockers_only and str(m.get("id", "")) not in blocker_ids:
            continue
        if human_only and not _is_human_task(artifact):
            continue
        rows.append(
            {
                "id": str(m.get("id", "")),
                "type": row_type,
                "status": str(m.get("status", "")),
                "project": _artifact_project(artifact),
                "human": "true" if _is_human_task(artifact) else "false",
                "title": str(m.get("title", "")),
                "path": str(artifact.file_path.relative_to(root)),
            }
        )

    rows.sort(key=lambda r: (r["type"], r["id"]))

    if not rows:
        print("No artifacts found")
        return 0

    for row in rows:
        print(
            f"{row['id']}\t{row['type']}\t{row['status']}\tproject={row['project'] or '-'}\thuman={row['human']}\t{row['title']}\t{row['path']}"
        )

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifact = _find_by_id(root, args.id)
    if not artifact:
        print(f"Artifact not found: {args.id}")
        return 1

    print(f"# {artifact.metadata.get('id')} {artifact.metadata.get('title')}")
    print(f"type: {artifact.metadata.get('type')}")
    print(f"status: {artifact.metadata.get('status')}")
    print(f"path: {artifact.file_path.relative_to(root)}")
    print()
    print(_dump_simple_yaml(artifact.metadata).rstrip())
    print("---")
    print(artifact.body.rstrip())
    return 0


def _cmd_set_status(args: argparse.Namespace, action: str) -> int:
    root = Path(args.root).resolve()
    artifact = _must_find_by_id(root, args.id)

    current = str(artifact.metadata.get("status", ""))
    artifact.metadata["status"] = _transition_status(current, action)
    artifact.metadata["updated_at"] = _now_iso()
    _write_artifact(artifact)

    _regenerate_indexes(root)
    print(f"{artifact.metadata.get('id')} status: {current} -> {artifact.metadata.get('status')}")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    return _cmd_set_status(args, "start")


def cmd_complete(args: argparse.Namespace) -> int:
    return _cmd_set_status(args, "complete")


def cmd_cancel(args: argparse.Namespace) -> int:
    return _cmd_set_status(args, "cancel")


def cmd_archive(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifact = _must_find_by_id(root, args.plan_id)
    if artifact.metadata.get("type") != "plan":
        raise ValueError(f"{args.plan_id} is not a plan")

    plan_dir = _find_plan_dir(root, str(artifact.metadata["id"]))
    archive_dir = root / ".train/plans/.archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / plan_dir.name

    if target.exists():
        raise ValueError(f"archive target already exists: {target.relative_to(root)}")

    plan_dir.rename(target)
    _regenerate_indexes(root)
    print(f"Archived {args.plan_id} -> {target.relative_to(root)}")
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    rows: list[str] = []

    for artifact in _collect_artifacts(root):
        status = str(artifact.metadata.get("status", ""))
        if status != "in_progress":
            continue
        rows.append(
            "\t".join(
                [
                    str(artifact.metadata.get("id", "")),
                    str(artifact.metadata.get("type", "")),
                    status,
                    str(artifact.metadata.get("title", "")),
                    str(artifact.file_path.relative_to(root)),
                ]
            )
        )

    if not rows:
        print("No in-progress artifacts")
        return 0

    for row in sorted(rows):
        print(row)
    return 0


def cmd_recent(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    completed: list[tuple[str, str, str, str, str]] = []

    for artifact in _collect_artifacts(root):
        status = str(artifact.metadata.get("status", ""))
        if status != "completed":
            continue
        completed.append(
            (
                str(artifact.metadata.get("updated_at", "")),
                str(artifact.metadata.get("id", "")),
                str(artifact.metadata.get("type", "")),
                str(artifact.metadata.get("title", "")),
                str(artifact.file_path.relative_to(root)),
            )
        )

    if not completed:
        print("No recently completed artifacts")
        return 0

    completed.sort(reverse=True)
    for updated_at, artifact_id, artifact_type, title, path in completed[: args.limit]:
        print(f"{updated_at}\t{artifact_id}\t{artifact_type}\tcompleted\t{title}\t{path}")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifacts = _collect_artifacts(root)
    chosen = _select_next_artifact(artifacts, project=(args.project or "").strip() or None)
    if chosen:
        print(
            f"{chosen.metadata.get('id')}\t{chosen.metadata.get('type')}\t{chosen.metadata.get('status')}\t{chosen.metadata.get('title')}\t{chosen.file_path.relative_to(root)}"
        )
        return 0

    print("No next artifact found")
    return 0


def _colorize(text: str, color: str, enabled: bool) -> str:
    if not enabled:
        return text
    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "bold": "\033[1m",
    }
    reset = "\033[0m"
    return f"{colors.get(color, '')}{text}{reset}" if color in colors else text


def _status_color(status: str) -> str:
    return {
        "open": "yellow",
        "in_progress": "blue",
        "completed": "green",
        "canceled": "magenta",
    }.get(status, "cyan")


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


def cmd_tree(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifacts = _collect_artifacts(root)
    project = (args.project or "").strip() or None
    lines = _render_open_tree_lines(artifacts, root, project=project, color_enabled=not args.no_color)
    if not lines:
        print("No open plan tree found")
        return 0
    for line in lines:
        print(line)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    color_enabled = not args.no_color
    project = (args.project or "").strip() or None
    artifacts = _collect_artifacts(root)
    blockers = _blocking_ids(artifacts)
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts}

    print(_colorize("== Trains Report ==", "bold", color_enabled))
    if project:
        print(f"project: {project}")
    print()

    print(_colorize("[In Progress]", "cyan", color_enabled))
    in_progress = _report_rows(artifacts, root, status="in_progress", project=project)
    if in_progress:
        for row in in_progress:
            parts = row.split("\t")
            parts[2] = _colorize(parts[2], _status_color(parts[2]), color_enabled)
            print("\t".join(parts))
    else:
        print("none")
    print()

    print(_colorize("[Next]", "cyan", color_enabled))
    nxt = _select_next_artifact(artifacts, project=project)
    if nxt:
        status = str(nxt.metadata.get("status", ""))
        print(
            "\t".join(
                [
                    str(nxt.metadata.get("id", "")),
                    str(nxt.metadata.get("type", "")),
                    _colorize(status, _status_color(status), color_enabled),
                    str(nxt.metadata.get("title", "")),
                    str(nxt.file_path.relative_to(root)),
                ]
            )
        )
    else:
        print("none")
    print()

    print(_colorize("[Blocking Human Tasks]", "cyan", color_enabled))
    human_blockers: list[str] = []
    for blocker_id in sorted(blockers):
        artifact = by_id.get(blocker_id)
        if not artifact:
            continue
        if project and _artifact_project(artifact) != project:
            continue
        if not _is_human_task(artifact):
            continue
        human_blockers.append(
            "\t".join(
                [
                    blocker_id,
                    "task",
                    str(artifact.metadata.get("status", "")),
                    str(artifact.metadata.get("title", "")),
                    str(artifact.file_path.relative_to(root)),
                ]
            )
        )
    if human_blockers:
        for row in human_blockers:
            print(row)
    else:
        print("none")
    print()

    print(_colorize("[Recent Completed]", "cyan", color_enabled))
    completed = [
        a
        for a in artifacts
        if str(a.metadata.get("status", "")) == "completed"
        and (not project or _artifact_project(a) == project)
    ]
    completed.sort(key=lambda a: str(a.metadata.get("updated_at", "")), reverse=True)
    if completed:
        for artifact in completed[: args.limit]:
            status = str(artifact.metadata.get("status", ""))
            print(
                "\t".join(
                    [
                        str(artifact.metadata.get("updated_at", "")),
                        str(artifact.metadata.get("id", "")),
                        str(artifact.metadata.get("type", "")),
                        _colorize(status, _status_color(status), color_enabled),
                        str(artifact.metadata.get("title", "")),
                    ]
                )
            )
    else:
        print("none")
    print()

    print(_colorize("[Open Plan Tree]", "cyan", color_enabled))
    tree_lines = _render_open_tree_lines(artifacts, root, project=project, color_enabled=color_enabled)
    if not tree_lines:
        print("none")
        return 0
    for line in tree_lines:
        print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="train", description="Trains CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize train directories and defaults")
    init_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    init_parser.add_argument("--force", action="store_true", help="Overwrite default scaffold files")
    init_parser.set_defaults(func=cmd_init)

    doctor_parser = subparsers.add_parser("doctor", help="Validate basic train workspace structure")
    doctor_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    doctor_parser.set_defaults(func=cmd_doctor)

    new_parser = subparsers.add_parser("new", help="Create new artifacts")
    new_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    new_subparsers = new_parser.add_subparsers(dest="artifact", required=True)

    plan_parser = new_subparsers.add_parser("plan", help="Create a plan")
    plan_parser.add_argument("title", help="Plan title")
    plan_parser.add_argument("--description", default="", help="Plan description")
    plan_parser.add_argument("--priority", default="medium", help="Priority (low|medium|high)")
    plan_parser.add_argument("--model", default="gpt-5", help="Default model")
    plan_parser.add_argument("--project", default="", help="Optional project key")
    plan_parser.set_defaults(func=cmd_new_plan)

    chunk_parser = new_subparsers.add_parser("chunk", help="Create a chunk")
    chunk_parser.add_argument("plan_id", help="Owning plan ID (e.g., PLAN-001)")
    chunk_parser.add_argument("title", help="Chunk title")
    chunk_parser.add_argument("--description", default="", help="Chunk description")
    chunk_parser.add_argument("--priority", default="medium", help="Priority (low|medium|high)")
    chunk_parser.add_argument("--model", default="gpt-5", help="Default model")
    chunk_parser.add_argument("--project", default="", help="Optional project key")
    chunk_parser.set_defaults(func=cmd_new_chunk)

    task_parser = new_subparsers.add_parser("task", help="Create a task")
    task_parser.add_argument("chunk_id", help="Owning chunk ID (e.g., CHUNK-001)")
    task_parser.add_argument("title", help="Task title")
    task_parser.add_argument("--description", default="", help="Task description")
    task_parser.add_argument("--model", default="gpt-5-mini", help="Model")
    task_parser.add_argument("--project", default="", help="Optional project key")
    task_parser.add_argument("--human", action="store_true", help="Mark task as human-required")
    task_parser.set_defaults(func=cmd_new_task)

    list_parser = subparsers.add_parser("list", help="List artifacts")
    list_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    list_parser.add_argument(
        "--type",
        default="all",
        choices=["all", "plan", "chunk", "task"],
        help="Filter by artifact type",
    )
    list_parser.add_argument("--project", default="", help="Filter by project key")
    list_parser.add_argument("--blocking", action="store_true", help="Only artifacts currently blocking others")
    list_parser.add_argument("--human", action="store_true", help="Only human tasks")
    list_parser.set_defaults(func=cmd_list)

    show_parser = subparsers.add_parser("show", help="Show one artifact")
    show_parser.add_argument("id", help="Artifact ID (PLAN-###, CHUNK-###, TASK-###)")
    show_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    show_parser.set_defaults(func=cmd_show)

    start_parser = subparsers.add_parser("start", help="Move artifact to in_progress")
    start_parser.add_argument("id", help="Artifact ID")
    start_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    start_parser.set_defaults(func=cmd_start)

    complete_parser = subparsers.add_parser("complete", help="Move artifact to completed")
    complete_parser.add_argument("id", help="Artifact ID")
    complete_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    complete_parser.set_defaults(func=cmd_complete)

    cancel_parser = subparsers.add_parser("cancel", help="Move artifact to canceled")
    cancel_parser.add_argument("id", help="Artifact ID")
    cancel_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    cancel_parser.set_defaults(func=cmd_cancel)

    archive_parser = subparsers.add_parser("archive", help="Archive a plan")
    archive_parser.add_argument("plan_id", help="Plan ID (PLAN-###)")
    archive_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    archive_parser.set_defaults(func=cmd_archive)

    progress_parser = subparsers.add_parser("progress", help="Show in-progress artifacts")
    progress_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    progress_parser.set_defaults(func=cmd_progress)

    recent_parser = subparsers.add_parser("recent", help="Show recently completed artifacts")
    recent_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    recent_parser.add_argument("--limit", type=int, default=10, help="Max items to show")
    recent_parser.set_defaults(func=cmd_recent)

    next_parser = subparsers.add_parser("next", help="Suggest next open artifact")
    next_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    next_parser.add_argument("--project", default="", help="Filter by project key")
    next_parser.set_defaults(func=cmd_next)

    tree_parser = subparsers.add_parser("tree", help="Show open plan/chunk/task tree")
    tree_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    tree_parser.add_argument("--project", default="", help="Filter by project key")
    tree_parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    tree_parser.set_defaults(func=cmd_tree)

    report_parser = subparsers.add_parser("report", help="Show consolidated colored status report")
    report_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    report_parser.add_argument("--project", default="", help="Filter by project key")
    report_parser.add_argument("--limit", type=int, default=10, help="Max recent items to show")
    report_parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    report_parser.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
