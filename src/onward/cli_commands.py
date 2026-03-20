"""Onward CLI command implementations (parser and entrypoint live in onward.cli)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from onward.artifacts import (
    _append_note,
    _artifact_glob,
    _artifact_project,
    _blocking_ids,
    _collect_artifacts,
    _find_by_id,
    _find_plan_dir,
    _format_artifact,
    _is_human_task,
    _must_find_by_id,
    _next_id,
    _parse_artifact,
    _read_notes,
    _regenerate_indexes,
    _render_open_tree_lines,
    _report_rows,
    _select_next_artifact,
    _transition_status,
    _update_artifact_status,
    _validate_artifact,
    _write_artifact,
)
from onward.config import (
    _config_model,
    _load_config,
    _load_template,
    _model_alias,
    _work_sequential_by_default,
    validate_config_contract_issues,
)
from onward.execution import (
    _collect_run_records,
    _execute_plan_review,
    _latest_run_for,
    _load_ongoing,
    _ordered_ready_chunk_tasks,
    _run_chunk_post_markdown_hook,
    _work_task,
)
from onward.scaffold import (
    DEFAULT_DIRECTORIES,
    DEFAULT_FILES,
    GITIGNORE_LINES,
    REQUIRED_PATHS,
    _require_workspace,
    _update_gitignore,
    _write_file,
)
from onward.sync import (
    cmd_sync_pull as _cmd_sync_pull,
    cmd_sync_push as _cmd_sync_push,
    cmd_sync_status as _cmd_sync_status,
    validate_sync_config,
)
from onward.split import (
    _assert_writes_safe,
    _normalize_chunk_candidates,
    _normalize_task_candidates,
    _parse_split_payload,
    _prepare_chunk_writes,
    _prepare_task_writes,
    _run_split_model,
)
from onward.util import (
    _clean_string,
    _colorize,
    _dump_simple_yaml,
    _now_iso,
    _parse_simple_yaml,
    _slugify,
    _split_frontmatter,
    _status_color,
)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


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

    config = _load_config(root)
    issues.extend(validate_config_contract_issues(config))
    issues.extend(validate_sync_config(root, config))

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


def cmd_sync_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    code, lines = _cmd_sync_status(root)
    for line in lines:
        print(line)
    return code


def cmd_sync_push(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    code, lines = _cmd_sync_push(root)
    for line in lines:
        print(line)
    return code


def cmd_sync_pull(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    code, lines = _cmd_sync_pull(root)
    for line in lines:
        print(line)
    return code


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

    artifact_id = str(artifact.metadata.get("id", ""))
    if str(artifact.metadata.get("type", "")) == "task":
        run = _latest_run_for(root, artifact_id)
        if run:
            print()
            print("Latest run:")
            print(f"  id: {run.get('id')}")
            print(f"  status: {run.get('status')}")
            print(f"  started_at: {run.get('started_at')}")
            print(f"  finished_at: {run.get('finished_at')}")
            print(f"  log: {run.get('log_path')}")
            if run.get("error"):
                print(f"  error: {run.get('error')}")
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifact = _must_find_by_id(root, args.id)
    artifact_id = str(artifact.metadata.get("id", ""))

    message = getattr(args, "message", None)
    if message:
        path = _append_note(root, artifact, message)
        print(f"Note added to {artifact_id} at {path.relative_to(root)}")
        return 0

    notes = _read_notes(root, artifact_id)
    if not notes.strip():
        print(f"No notes for {artifact_id}.")
        return 0

    print(f"Notes for {artifact_id}:\n")
    print(notes.rstrip())
    return 0


def _cmd_set_status(args: argparse.Namespace, action: str) -> int:
    root = Path(args.root).resolve()
    artifact = _must_find_by_id(root, args.id)

    current = str(artifact.metadata.get("status", ""))
    artifact.metadata["status"] = _transition_status(current, action)
    artifact.metadata["updated_at"] = _now_iso()
    _write_artifact(artifact)

    _regenerate_indexes(root)
    artifact_id = str(artifact.metadata.get("id", ""))
    print(f"{artifact_id} status: {current} -> {artifact.metadata.get('status')}")

    if action in {"complete", "cancel"}:
        notes = _read_notes(root, artifact_id)
        if notes.strip():
            print(f"\nRelated notes for {artifact_id}:\n")
            print(notes.rstrip())

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


def cmd_review_plan(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    _require_workspace(root)
    plan = _must_find_by_id(root, args.plan_id)
    plan_type = str(plan.metadata.get("type", ""))
    if plan_type != "plan":
        raise ValueError(f"{args.plan_id} is not a plan (type={plan_type})")

    config = _load_config(root)
    default_model = _config_model(config, "default", "opus-latest")
    review_model = _config_model(config, "review_default", default_model)

    review_cfg = config.get("review", {})
    if not isinstance(review_cfg, dict):
        review_cfg = {}
    double = review_cfg.get("double_review", True)
    if isinstance(double, str):
        double = double.strip().lower() in {"1", "true", "yes", "y"}

    models: list[tuple[str, str]] = []
    models.append((_model_alias(review_model), "reviewer-1"))
    if double:
        models.append((_model_alias(default_model), "reviewer-2"))

    prompt_path = root / ".onward/prompts/review-plan.md"
    if prompt_path.exists():
        prompt = prompt_path.read_text(encoding="utf-8")
    else:
        prompt = "Review this plan for gaps, security issues, missing requirements, and deployment risks."

    plan_id = str(plan.metadata.get("id", ""))
    review_paths: list[Path] = []

    for model, label in models:
        print(f"Running review: {label} (model={model})...")
        ok, review_path = _execute_plan_review(root, plan, model, label, prompt)
        if ok:
            review_paths.append(review_path)
            print(f"  -> {review_path.relative_to(root)}")
        else:
            print(f"  -> Review {label} failed.")

    if not review_paths:
        print(f"\nNo reviews completed for {plan_id}.")
        return 1

    print()
    print(f"Review complete for {plan_id}. {len(review_paths)} review(s) written:")
    for rp in review_paths:
        print(f"  {rp.relative_to(root)}")
    print()
    print("Recommendation: read through the review(s) and judiciously incorporate")
    print("findings into the plan before splitting or starting work.")
    return 0


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
    config = _load_config(root)
    sequential = _work_sequential_by_default(config)
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
            print(
                f"Chunk {chunk_id} is usually still in_progress; fix the task or run "
                f"onward work {chunk_id} again. See docs/LIFECYCLE.md"
            )
            return 1
        if not sequential:
            ready_again, all_resolved_again = _ordered_ready_chunk_tasks(root, chunk_id)
            if ready_again:
                print(
                    f"Chunk {chunk_id}: stopping after one task (work.sequential_by_default is false); "
                    "run onward work again to continue."
                )
                return 0
            if not all_resolved_again:
                print(f"Chunk {chunk_id} has unresolved task dependencies")
                return 1

    refreshed_chunk = _must_find_by_id(root, chunk_id)
    hook_ok, hook_error = _run_chunk_post_markdown_hook(root, refreshed_chunk)
    if not hook_ok:
        print(f"Chunk {chunk_id} post hook failed: {hook_error}")
        return 1
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
    default_model = _config_model(config, "default", "opus-latest")
    split_model = _clean_string(args.model) or _config_model(config, "split_default", "") or default_model
    task_default_model = _config_model(config, "task_default", "sonnet-latest")

    prompt_name = "split-plan.md" if artifact_type == "plan" else "split-chunk.md"
    raw = _run_split_model(artifact, prompt_name, split_model, task_default_model)

    if artifact_type == "plan":
        parsed = _parse_split_payload(raw, "chunks")
        normalized = _normalize_chunk_candidates(parsed, default_model)
        writes = _prepare_chunk_writes(root, artifact, normalized)
    else:
        parsed = _parse_split_payload(raw, "tasks")
        normalized = _normalize_task_candidates(parsed, task_default_model)
        writes = _prepare_task_writes(root, artifact, normalized)

    _assert_writes_safe(root, writes)

    if args.dry_run:
        print(f"Split dry-run for {args.id} using model={split_model}")
        print(f"Prompt: .onward/prompts/{prompt_name}")
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
    rows: list[tuple[str, str, str, str, str, str]] = []

    for artifact in _collect_artifacts(root):
        status = str(artifact.metadata.get("status", ""))
        if status != "completed":
            continue
        rows.append(
            (
                str(artifact.metadata.get("updated_at", "")),
                str(artifact.metadata.get("id", "")),
                str(artifact.metadata.get("type", "")),
                "completed",
                str(artifact.metadata.get("title", "")),
                str(artifact.file_path.relative_to(root)),
            )
        )

    for rec in _collect_run_records(root):
        finished = str(rec.get("finished_at") or rec.get("started_at", ""))
        status = str(rec.get("status", ""))
        if status not in {"completed", "failed"}:
            continue
        target = str(rec.get("target", ""))
        rows.append(
            (
                finished,
                str(rec.get("id", "")),
                "run",
                status,
                target,
                str(rec.get("log_path", "")),
            )
        )

    if not rows:
        print("No recently completed artifacts")
        return 0

    rows.sort(reverse=True)
    for timestamp, item_id, item_type, status, title_or_target, path in rows[: args.limit]:
        print(f"{timestamp}\t{item_id}\t{item_type}\t{status}\t{title_or_target}\t{path}")
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

