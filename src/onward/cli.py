from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_DIRECTORIES = [
    ".onward/plans",
    ".onward/plans/.archive",
    ".onward/templates",
    ".onward/prompts",
    ".onward/hooks",
    ".onward/sync",
    ".onward/runs",
]

DEFAULT_FILES = {
    ".onward.config.yaml": """# Onward workspace config.
# This file is read by the CLI at runtime. Keep it in repo root.

# Schema version for future migrations.
version: 1

paths:
  # Canonical directory for plan/chunk/task artifacts and derived indexes.
  plans_dir: .onward/plans
  # Runtime state root for ongoing runs, logs, and ephemeral execution files.
  runtime_dir: .onward

sync:
  # Sync mode: local (disabled), branch (same repo branch), repo (separate repo).
  mode: local
  # Branch name used when sync mode is "branch".
  branch: onward
  # Optional separate git repository URL/path used when mode is "repo".
  repo: null
  # Local worktree path used for sync staging operations.
  worktree_path: .onward/sync

ralph:
  # Executor command to run for `onward work` task execution.
  command: ralph
  # Default arguments appended to the executor command.
  args: []
  # Global on/off switch for executor usage.
  enabled: true

models:
  # Fallback model for generic operations when no more specific model is set.
  default: gpt-5
  # Default model for newly created tasks.
  task_default: gpt-5-mini
  # Default model used by `onward split` decomposition.
  split_default: gpt-5
  # Default model for review-oriented hooks/workflows.
  review_default: gpt-5

work:
  # If true, chunk execution runs tasks sequentially unless explicitly overridden.
  sequential_by_default: true
  # If true, execution may create a dedicated git worktree for isolated work.
  create_worktree: true
  # Parent directory where execution worktrees are created.
  worktree_root: .worktrees
  # Base branch used when creating new worktrees.
  base_branch: main

hooks:
  # Shell commands run before each task (empty list means disabled).
  pre_task_shell: []
  # Shell commands run after each task (empty list means disabled).
  post_task_shell: []
  # Optional markdown hook path executed before each task (null disables).
  pre_task_markdown: null
  # Optional markdown hook path executed after each task.
  post_task_markdown: .onward/hooks/post-task.md
  # Optional markdown hook path executed after chunk completion.
  post_chunk_markdown: .onward/hooks/post-chunk.md
""",
    ".onward/templates/plan.md": """# Summary

<!-- For a semi-technical layperson: What does this scope of work accomplish? 2-4 sentences, not in the weeds. -->

# Problem

<!-- Optional -->

# Goals

<!-- Bullets -->

# Non-goals

<!-- Bullets -->

# End state

<!-- A checklist of user stories representing the ideal end state. -->

# Context

<!-- Optional -->

# Proposed approach

<!-- This section could be huge. As big as it needs to. Hundreds of lines. The goal is to exhaustively specify the plan. Everything we intend to do. Files, tests, connections, etc. -->

# Key artifacts

<!-- Optional. If relevant, any ENVs, processes, etc that may need to be documented or acted on when the work is complete. -->

# Acceptance criteria

<!-- Specific tests, e2es, QA assertions, file existences, documentation, etc, that attest to the successful completion of the work -->

# Notes

<!-- Optional -->
""",
    ".onward/templates/chunk.md": """# Summary

<!-- For a semi-technical layperson: what this chunk ships and why it matters. -->

# Scope

<!-- Concrete bullets of what is in this chunk. -->

# Out of scope

<!-- Concrete bullets of what is explicitly not included. -->

# Dependencies

<!-- IDs, systems, or decisions that must exist first. -->

# Expected files/systems involved

<!-- List likely files, directories, services, and tables touched. -->

# Completion criteria

<!-- Checklist that can be verified by tests/review. -->

# Notes

<!-- Optional -->
""",
    ".onward/templates/task.md": """# Context

<!-- What this task is doing and where it fits in the chunk. -->

# Scope

<!-- Tight, concrete bullets. Keep this task small and finishable. -->

# Out of scope

<!-- Explicitly exclude adjacent work. -->

# Files to inspect

<!-- Start here. Include exact paths when known. -->

# Implementation notes

<!-- Constraints, gotchas, and edge cases to handle. -->

# Acceptance criteria

<!-- Binary checks: tests, outputs, behavior changes, docs updates. -->

# Handoff notes

<!-- What the parent/next worker should know. Include follow-up ideas if discovered. -->
""",
    ".onward/templates/run.md": """# Execution summary

<!-- Short narrative of what was attempted and result. -->

# Inputs

<!-- Task ID, model/executor, important context passed in. -->

# Output

<!-- Key output, files changed, and notable terminal/log details. -->

# Follow-up

<!-- Blockers, refactors, or for-later tasks discovered during execution. -->
""",
    ".onward/prompts/split-plan.md": """You are decomposing a plan into executable chunks.

Output strict JSON with this exact shape:
{
  "chunks": [
    {
      "title": "string",
      "description": "string",
      "priority": "low|medium|high",
      "model": "string"
    }
  ]
}

Constraints:
- Return at least one chunk.
- Keep chunk titles short and concrete.
- Do not include markdown fences or any non-JSON text.
""",
    ".onward/prompts/split-chunk.md": """You are decomposing a chunk into executable tasks.

Output strict JSON with this exact shape:
{
  "tasks": [
    {
      "title": "string",
      "description": "string",
      "acceptance": ["string"],
      "model": "string",
      "human": false
    }
  ]
}

Constraints:
- Return at least one task.
- Each task must include one or more acceptance checks.
- Do not include markdown fences or any non-JSON text.
""",
    ".onward/hooks/post-task.md": """---
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
    ".onward/hooks/post-chunk.md": """---
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
    ".onward/plans/index.yaml": """generated_at: null
plans: []
chunks: []
tasks: []
runs: []
""",
    ".onward/plans/recent.yaml": """generated_at: null
completed: []
""",
    ".onward/ongoing.json": """{
  "version": 1,
  "updated_at": null,
  "active_runs": []
}
""",
}

GITIGNORE_LINES = [
    ".onward/plans/.archive/",
    ".onward/runs/",
    ".onward/ongoing.json",
    ".dogfood/",
]

REQUIRED_PATHS = [
    ".onward.config.yaml",
    ".onward/templates/plan.md",
    ".onward/templates/chunk.md",
    ".onward/templates/task.md",
    ".onward/templates/run.md",
    ".onward/prompts/split-plan.md",
    ".onward/prompts/split-chunk.md",
    ".onward/plans/index.yaml",
    ".onward/plans/recent.yaml",
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


def _is_workspace_root(root: Path) -> bool:
    return (
        (root / ".onward.config.yaml").exists()
        and (root / ".onward").exists()
        and (root / ".onward/plans").exists()
    )


def _require_workspace(root: Path) -> None:
    if _is_workspace_root(root):
        return
    raise ValueError(
        f"not an Onward workspace: {root}. Run `onward init` here (or pass --root <workspace>)"
    )


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


def _load_template(root: Path, artifact_type: str) -> str:
    return (root / f".onward/templates/{artifact_type}.md").read_text(encoding="utf-8")


def _load_prompt(root: Path, prompt_name: str) -> str:
    return (root / f".onward/prompts/{prompt_name}").read_text(encoding="utf-8")


def _load_config(root: Path) -> dict[str, Any]:
    config_path = root / ".onward.config.yaml"
    if not config_path.exists():
        return {}
    parsed = _parse_simple_yaml(config_path.read_text(encoding="utf-8"))
    if isinstance(parsed, dict):
        return parsed
    return {}


def _config_model(config: dict[str, Any], key: str, fallback: str) -> str:
    models = config.get("models", {})
    if isinstance(models, dict):
        value = str(models.get(key, "")).strip()
        if value:
            return value
    return fallback


def _markdown_section(body: str, heading: str) -> str:
    target = heading.strip().lower()
    lines = body.splitlines()
    start = -1
    for i, line in enumerate(lines):
        match = re.match(r"^#{1,6}\s+(.*)$", line.strip())
        if not match:
            continue
        if match.group(1).strip().lower() == target:
            start = i + 1
            break
    if start < 0:
        return ""
    end = len(lines)
    for i in range(start, len(lines)):
        if re.match(r"^#{1,6}\s+", lines[i].strip()):
            end = i
            break
    return "\n".join(lines[start:end]).strip()


def _extract_markdown_list_items(section: str) -> list[str]:
    items: list[str] = []
    for line in section.splitlines():
        match = re.match(r"^\s*(?:-|\d+\.)\s+(.+?)\s*$", line)
        if match:
            value = match.group(1).strip()
            if value:
                items.append(value)
    return items


def _heuristic_split_plan_payload(artifact: Artifact, default_model: str) -> dict[str, Any]:
    strategy_items = _extract_markdown_list_items(_markdown_section(artifact.body, "Chunking strategy"))
    goal_items = _extract_markdown_list_items(_markdown_section(artifact.body, "Goals"))
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
    scope_items = _extract_markdown_list_items(_markdown_section(artifact.body, "Scope"))
    completion_items = _extract_markdown_list_items(_markdown_section(artifact.body, "Completion criteria"))
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


def _run_split_model(
    artifact: Artifact,
    prompt_name: str,
    model: str,
    default_task_model: str,
) -> str:
    # Temporary bridge until executor-backed model calls are wired in.
    env_override = str(os.environ.get("TRAIN_SPLIT_RESPONSE", "")).strip()
    if env_override:
        return env_override
    if prompt_name == "split-plan.md":
        payload = _heuristic_split_plan_payload(artifact, model)
    else:
        payload = _heuristic_split_chunk_payload(artifact, default_task_model)
    return json.dumps(payload, indent=2)


def _parse_split_payload(raw: str, key: str) -> list[dict[str, Any]]:
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


def _clean_string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_priority(value: Any) -> str:
    priority = _clean_string(value).lower()
    return priority if priority in {"low", "medium", "high"} else "medium"


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _clean_string(value).lower() in {"1", "true", "yes", "y"}


def _normalize_acceptance(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    single = _clean_string(value)
    return [single] if single else []


def _normalize_chunk_candidates(items: list[dict[str, Any]], default_model: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, item in enumerate(items, start=1):
        title = _clean_string(item.get("title"))
        description = _clean_string(item.get("description"))
        if not title:
            raise ValueError(f"split validation failed: chunks[{i}].title is required")
        if not description:
            raise ValueError(f"split validation failed: chunks[{i}].description is required")
        model = _clean_string(item.get("model")) or default_model
        out.append(
            {
                "title": title,
                "description": description,
                "priority": _normalize_priority(item.get("priority")),
                "model": model,
            }
        )
    return out


def _normalize_task_candidates(items: list[dict[str, Any]], default_model: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, item in enumerate(items, start=1):
        title = _clean_string(item.get("title"))
        description = _clean_string(item.get("description"))
        acceptance = _normalize_acceptance(item.get("acceptance"))
        if not title:
            raise ValueError(f"split validation failed: tasks[{i}].title is required")
        if not description:
            raise ValueError(f"split validation failed: tasks[{i}].description is required")
        if not acceptance:
            raise ValueError(f"split validation failed: tasks[{i}].acceptance is required")
        model = _clean_string(item.get("model")) or default_model
        if not model:
            raise ValueError(f"split validation failed: tasks[{i}].model is required")
        out.append(
            {
                "title": title,
                "description": description,
                "acceptance": acceptance,
                "model": model,
                "human": _normalize_bool(item.get("human")),
            }
        )
    return out


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


def _prepare_chunk_writes(
    root: Path,
    plan_artifact: Artifact,
    candidates: list[dict[str, Any]],
) -> list[tuple[str, Path, str]]:
    plan_id = str(plan_artifact.metadata.get("id"))
    plan_dir = _find_plan_dir(root, plan_id)
    chunk_ids = _next_ids(root, "CHUNK", len(candidates))
    now = _now_iso()
    writes: list[tuple[str, Path, str]] = []
    for chunk_id, candidate in zip(chunk_ids, candidates):
        target = plan_dir / "chunks" / f"{chunk_id}-{_slugify(candidate['title'])}.md"
        metadata = {
            "id": chunk_id,
            "type": "chunk",
            "plan": plan_id,
            "project": _artifact_project(plan_artifact),
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
        writes.append((chunk_id, target, _format_artifact(metadata, body)))
    return writes


def _prepare_task_writes(
    root: Path,
    chunk_artifact: Artifact,
    candidates: list[dict[str, Any]],
) -> list[tuple[str, Path, str]]:
    plan_id = str(chunk_artifact.metadata.get("plan"))
    chunk_id = str(chunk_artifact.metadata.get("id"))
    plan_dir = _find_plan_dir(root, plan_id)
    task_ids = _next_ids(root, "TASK", len(candidates))
    now = _now_iso()
    writes: list[tuple[str, Path, str]] = []
    for task_id, candidate in zip(task_ids, candidates):
        target = plan_dir / "tasks" / f"{task_id}-{_slugify(candidate['title'])}.md"
        metadata = {
            "id": task_id,
            "type": "task",
            "plan": plan_id,
            "chunk": chunk_id,
            "project": _artifact_project(chunk_artifact),
            "title": candidate["title"],
            "status": "open",
            "description": candidate["description"],
            "human": candidate["human"],
            "model": candidate["model"],
            "executor": "ralph",
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
        writes.append((task_id, target, _format_artifact(metadata, body)))
    return writes


def _assert_writes_safe(root: Path, writes: list[tuple[str, Path, str]]) -> None:
    seen: set[Path] = set()
    for _artifact_id, path, _content in writes:
        if path in seen:
            raise ValueError(f"split write collision: duplicate output path {path.relative_to(root)}")
        seen.add(path)
        if path.exists():
            raise ValueError(f"split write collision: target already exists {path.relative_to(root)}")


def _model_alias(model: str) -> str:
    normalized = model.strip().lower().replace("_", "-")
    aliases = {
        "opus": "claude-opus-4-1",
        "sonnet": "claude-sonnet-4",
        "haiku": "claude-haiku-4",
        "gpt5": "gpt-5",
    }
    return aliases.get(normalized, model.strip())


def _run_timestamp() -> str:
    return _now_iso().replace(":", "-")


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

    default_model = _config_model(config, "default", "gpt-5")
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

    payload = {
        "task": task.metadata,
        "body": task.body,
    }
    stdout = ""
    stderr = ""
    error = ""
    ok = False
    try:
        result = subprocess.run(
            cmd,
            input=json.dumps(payload, indent=2),
            text=True,
            capture_output=True,
            check=False,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        ok = result.returncode == 0
        if not ok:
            error = f"executor exited with code {result.returncode}"
    except FileNotFoundError:
        error = f"executor command not found: {command}"
    except Exception as exc:  # noqa: BLE001
        error = str(exc)

    log_lines = []
    log_lines.append(f"$ {' '.join(cmd)}")
    log_lines.append("")
    if stdout:
        log_lines.append("[stdout]")
        log_lines.append(stdout.rstrip())
    if stderr:
        if stdout:
            log_lines.append("")
        log_lines.append("[stderr]")
        log_lines.append(stderr.rstrip())
    if error:
        if stdout or stderr:
            log_lines.append("")
        log_lines.append(f"[error] {error}")
    run_log.write_text("\n".join(log_lines).rstrip() + "\n", encoding="utf-8")

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


def _update_artifact_status(root: Path, artifact: Artifact, status: str) -> None:
    artifact.metadata["status"] = status
    artifact.metadata["updated_at"] = _now_iso()
    _write_artifact(artifact)
    _regenerate_indexes(root)


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


def cmd_work(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifact = _must_find_by_id(root, args.id)
    artifact_type = str(artifact.metadata.get("type", ""))
    if artifact_type == "task":
        ok, run_id = _work_task(root, artifact)
        if run_id:
            print(f"Run {run_id}: {'completed' if ok else 'failed'}")
        else:
            print(f"{args.id} already completed")
        return 0 if ok else 1
    if artifact_type != "chunk":
        raise ValueError(f"{args.id} is not a task or chunk")

    chunk = artifact
    chunk_id = str(chunk.metadata.get("id", ""))
    if str(chunk.metadata.get("status", "")) in {"open", "in_progress"}:
        _update_artifact_status(root, chunk, "in_progress")

    while True:
        ready_tasks, all_resolved = _ordered_ready_chunk_tasks(root, chunk_id)
        if not ready_tasks:
            if not all_resolved:
                print(f"Chunk {chunk_id} has unresolved task dependencies")
                return 1
            break
        next_task = ready_tasks[0]
        ok, run_id = _work_task(root, next_task)
        print(f"Run {run_id}: {'completed' if ok else 'failed'}")
        if not ok:
            print(f"Stopping chunk work for {chunk_id} after task failure")
            return 1

    refreshed_chunk = _must_find_by_id(root, chunk_id)
    if str(refreshed_chunk.metadata.get("status", "")) in {"open", "in_progress"}:
        _update_artifact_status(root, refreshed_chunk, "completed")
    print(f"Chunk {chunk_id} completed")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifact = _must_find_by_id(root, args.id)
    artifact_type = str(artifact.metadata.get("type", ""))
    if artifact_type not in {"plan", "chunk"}:
        raise ValueError(f"{args.id} is not splittable (expected PLAN-* or CHUNK-*)")

    config = _load_config(root)
    split_model = _clean_string(args.model) or _config_model(config, "split_default", "gpt-5")
    task_default_model = _config_model(config, "task_default", "gpt-5-mini")

    prompt_name = "split-plan.md" if artifact_type == "plan" else "split-chunk.md"
    prompt = _load_prompt(root, prompt_name)
    prompt_context = "\n".join(
        [
            prompt.strip(),
            "",
            "Source artifact metadata (YAML-like):",
            _dump_simple_yaml(artifact.metadata).rstrip(),
            "",
            "Source artifact body:",
            artifact.body.strip(),
        ]
    )
    raw = _run_split_model(artifact, prompt_name, split_model, task_default_model)

    if artifact_type == "plan":
        parsed = _parse_split_payload(raw, "chunks")
        normalized = _normalize_chunk_candidates(parsed, _config_model(config, "default", "gpt-5"))
        writes = _prepare_chunk_writes(root, artifact, normalized)
    else:
        parsed = _parse_split_payload(raw, "tasks")
        normalized = _normalize_task_candidates(parsed, task_default_model)
        writes = _prepare_task_writes(root, artifact, normalized)

    _assert_writes_safe(root, writes)

    if args.dry_run:
        print(f"Split dry-run for {args.id} using model={split_model}")
        print(f"Prompt: .onward/prompts/{prompt_name}")
        print(f"Prompt context bytes: {len(prompt_context.encode('utf-8'))}")
        for artifact_id, path, _content in writes:
            print(f"PLAN: create {artifact_id}\t{path.relative_to(root)}")
        return 0

    for _artifact_id, path, content in writes:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _regenerate_indexes(root)

    for artifact_id, path, _content in writes:
        print(f"Created {artifact_id} at {path.relative_to(root)}")
    return 0


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

    print(f"Initialized Onward workspace in {root}")
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

    ongoing_path = root / ".onward/ongoing.json"
    if ongoing_path.exists():
        try:
            json.loads(ongoing_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(f"invalid json in .onward/ongoing.json: {exc}")

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

    plan_dir = root / ".onward/plans" / f"{plan_id}-{slug}"
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
    target_rel = str(target.relative_to(root))
    print(f"Created {plan_id} at {target_rel}")
    print(
        f"Plan created at {target_rel}. It is currently an empty template. Inspect it for guidance on how to fill it out."
    )
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
    archive_dir = root / ".onward/plans/.archive"
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
        ongoing = _load_ongoing(root)
        active = ongoing.get("active_runs", [])
        if not isinstance(active, list) or not active:
            print("No in-progress artifacts")
            return 0
    else:
        for row in sorted(rows):
            print(row)

    ongoing = _load_ongoing(root)
    active = ongoing.get("active_runs", [])
    if isinstance(active, list):
        for run in active:
            print(
                "\t".join(
                    [
                        str(run.get("id", "")),
                        "run",
                        str(run.get("status", "running")),
                        str(run.get("target", "")),
                        str(run.get("log_path", "")),
                    ]
                )
            )
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

    print(_colorize("== Onward Report ==", "bold", color_enabled))
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
    parser = argparse.ArgumentParser(prog="onward", description="Onward CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize onward directories and defaults")
    init_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    init_parser.add_argument("--force", action="store_true", help="Overwrite default scaffold files")
    init_parser.set_defaults(func=cmd_init)

    doctor_parser = subparsers.add_parser("doctor", help="Validate basic onward workspace structure")
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

    split_parser = subparsers.add_parser("split", help="Split a plan into chunks or a chunk into tasks")
    split_parser.add_argument("id", help="Artifact ID (PLAN-### or CHUNK-###)")
    split_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    split_parser.add_argument("--dry-run", action="store_true", help="Print planned artifacts without writing files")
    split_parser.add_argument("--model", default="", help="Override split model")
    split_parser.set_defaults(func=cmd_split)

    work_parser = subparsers.add_parser("work", help="Execute a task or sequentially execute a chunk")
    work_parser.add_argument("id", help="Artifact ID (TASK-### or CHUNK-###)")
    work_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    work_parser.set_defaults(func=cmd_work)

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
        if getattr(args, "command", "") != "init":
            root_value = getattr(args, "root", ".")
            _require_workspace(Path(root_value).resolve())
        return args.func(args)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
