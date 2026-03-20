"""Onward CLI command implementations (parser and entrypoint live in onward.cli)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from onward.artifacts import (
    append_note,
    artifact_glob,
    artifact_project,
    blocking_ids,
    collect_artifacts,
    find_by_id,
    find_plan_dir,
    format_artifact,
    is_human_task,
    must_find_by_id,
    next_id,
    parse_artifact,
    read_notes,
    regenerate_indexes,
    render_active_work_tree_lines,
    report_rows,
    select_next_artifact,
    transition_status,
    update_artifact_status,
    validate_artifact,
    write_artifact,
)
from onward.config import (
    build_plan_review_slots,
    config_raw_deprecation_warnings,
    load_artifact_template,
    load_workspace_config,
    model_setting,
    resolve_model_alias,
    validate_config_contract_issues,
    work_sequential_by_default,
)
from onward.preflight import preflight_shell_invocation
from onward.execution import (
    collect_run_records,
    execute_plan_review,
    finalize_chunks_all_tasks_terminal,
    latest_run_for,
    load_ongoing,
    ordered_ready_chunk_tasks,
    run_chunk_post_markdown_hook,
    work_task,
)
from onward.scaffold import (
    DEFAULT_DIRECTORIES,
    DEFAULT_FILES,
    GITIGNORE_LINES,
    REQUIRED_PATHS,
    require_workspace,
    update_gitignore,
    write_workspace_file,
)
from onward.sync import (
    cmd_sync_pull as _cmd_sync_pull,
    cmd_sync_push as _cmd_sync_push,
    cmd_sync_status as _cmd_sync_status,
    validate_sync_config,
)
from onward.split import (
    assert_writes_safe,
    normalize_chunk_candidates,
    normalize_task_candidates,
    parse_split_payload,
    prepare_chunk_writes,
    prepare_task_writes,
    run_split_model,
)
from onward.util import (
    clean_string,
    colorize,
    dump_simple_yaml,
    now_iso,
    parse_simple_yaml,
    slugify,
    split_frontmatter,
    status_color,
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
        wrote = write_workspace_file(root / rel_path, content, force=args.force)
        if wrote:
            created += 1

    gitignore_updated = update_gitignore(root)
    regenerate_indexes(root)

    print(f"Initialized Onward workspace in {root}")
    print(f"Created/updated files: {created}")
    if gitignore_updated:
        print("Updated .gitignore")

    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    issues: list[str] = []

    config_path = root / ".onward.config.yaml"
    raw_config: dict = {}
    if config_path.exists():
        raw_parsed = parse_simple_yaml(config_path.read_text(encoding="utf-8"))
        if isinstance(raw_parsed, dict):
            raw_config = raw_parsed
    for w in config_raw_deprecation_warnings(raw_config):
        print(f"Warning: {w}")

    config = load_workspace_config(root)
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
    for path in artifact_glob(root):
        try:
            artifact = parse_artifact(path)
        except Exception as exc:  # noqa: BLE001
            issues.append(str(exc))
            continue

        artifact_issues = validate_artifact(artifact)
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
    plan_id = next_id(root, "PLAN")
    now = now_iso()
    slug = slugify(args.title)

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

    body = load_artifact_template(root, "plan")
    target = plan_dir / "plan.md"
    target.write_text(format_artifact(metadata, body), encoding="utf-8")

    regenerate_indexes(root)
    target_rel = str(target.relative_to(root))
    print(f"Created {plan_id} at {target_rel}")
    print(
        f"Plan created at {target_rel}. It is currently an empty template. Inspect it for guidance on how to fill it out."
    )
    return 0


def cmd_new_chunk(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    plan_id = args.plan_id

    plan_dir = find_plan_dir(root, plan_id)
    chunk_id = next_id(root, "CHUNK")
    now = now_iso()
    slug = slugify(args.title)

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

    body = load_artifact_template(root, "chunk")
    target = plan_dir / "chunks" / f"{chunk_id}-{slug}.md"
    target.write_text(format_artifact(metadata, body), encoding="utf-8")

    regenerate_indexes(root)
    print(f"Created {chunk_id} at {target.relative_to(root)}")
    return 0


def cmd_new_task(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    chunk = find_by_id(root, args.chunk_id)
    if not chunk:
        raise ValueError(f"chunk not found: {args.chunk_id}")
    if chunk.metadata.get("type") != "chunk":
        raise ValueError(f"{args.chunk_id} is not a chunk")

    plan_id = str(chunk.metadata["plan"])
    chunk_id = str(chunk.metadata["id"])
    task_id = next_id(root, "TASK")
    now = now_iso()
    slug = slugify(args.title)

    plan_dir = find_plan_dir(root, plan_id)
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
        "executor": "onward-exec",
        "depends_on": [],
        "blocked_by": [],
        "files": [],
        "acceptance": [],
        "created_at": now,
        "updated_at": now,
    }

    body = load_artifact_template(root, "task")
    target = plan_dir / "tasks" / f"{task_id}-{slug}.md"
    target.write_text(format_artifact(metadata, body), encoding="utf-8")

    regenerate_indexes(root)
    print(f"Created {task_id} at {target.relative_to(root)}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifact_type = args.type
    project_filter = (args.project or "").strip()
    blockers_only = bool(args.blocking)
    human_only = bool(args.human)
    artifacts = collect_artifacts(root)
    blocker_ids = blocking_ids(artifacts) if blockers_only else set()

    rows: list[dict[str, str]] = []
    for artifact in artifacts:
        m = artifact.metadata
        row_type = str(m.get("type", ""))
        if artifact_type != "all" and row_type != artifact_type:
            continue
        if project_filter and artifact_project(artifact) != project_filter:
            continue
        if blockers_only and str(m.get("id", "")) not in blocker_ids:
            continue
        if human_only and not is_human_task(artifact):
            continue
        rows.append(
            {
                "id": str(m.get("id", "")),
                "type": row_type,
                "status": str(m.get("status", "")),
                "project": artifact_project(artifact),
                "human": "true" if is_human_task(artifact) else "false",
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
    artifact = find_by_id(root, args.id)
    if not artifact:
        print(f"Artifact not found: {args.id}")
        return 1

    print(f"# {artifact.metadata.get('id')} {artifact.metadata.get('title')}")
    print(f"type: {artifact.metadata.get('type')}")
    print(f"status: {artifact.metadata.get('status')}")
    print(f"path: {artifact.file_path.relative_to(root)}")
    print()
    print(dump_simple_yaml(artifact.metadata).rstrip())
    print("---")
    print(artifact.body.rstrip())

    artifact_id = str(artifact.metadata.get("id", ""))
    if str(artifact.metadata.get("type", "")) == "task":
        run = latest_run_for(root, artifact_id)
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
    artifact = must_find_by_id(root, args.id)
    artifact_id = str(artifact.metadata.get("id", ""))

    message = getattr(args, "message", None)
    if message:
        path = append_note(root, artifact, message)
        print(f"Note added to {artifact_id} at {path.relative_to(root)}")
        return 0

    notes = read_notes(root, artifact_id)
    if not notes.strip():
        print(f"No notes for {artifact_id}.")
        return 0

    print(f"Notes for {artifact_id}:\n")
    print(notes.rstrip())
    return 0


def _cmd_set_status(args: argparse.Namespace, action: str) -> int:
    root = Path(args.root).resolve()
    artifact = must_find_by_id(root, args.id)

    current = str(artifact.metadata.get("status", ""))
    artifact.metadata["status"] = transition_status(current, action)
    artifact.metadata["updated_at"] = now_iso()
    write_artifact(artifact)

    regenerate_indexes(root)
    artifact_id = str(artifact.metadata.get("id", ""))
    print(f"{artifact_id} status: {current} -> {artifact.metadata.get('status')}")

    if action == "complete":
        _, warnings = finalize_chunks_all_tasks_terminal(root)
        for w in warnings:
            print(w)

    if action in {"complete", "cancel"}:
        notes = read_notes(root, artifact_id)
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
    artifact = must_find_by_id(root, args.plan_id)
    if artifact.metadata.get("type") != "plan":
        raise ValueError(f"{args.plan_id} is not a plan")

    plan_dir = find_plan_dir(root, str(artifact.metadata["id"]))
    archive_dir = root / ".onward/plans/.archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / plan_dir.name

    if target.exists():
        raise ValueError(f"archive target already exists: {target.relative_to(root)}")

    plan_dir.rename(target)
    regenerate_indexes(root)
    print(f"Archived {args.plan_id} -> {target.relative_to(root)}")
    return 0


def cmd_review_plan(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    require_workspace(root)
    plan = must_find_by_id(root, args.plan_id)
    plan_type = str(plan.metadata.get("type", ""))
    if plan_type != "plan":
        raise ValueError(f"{args.plan_id} is not a plan (type={plan_type})")

    config = load_workspace_config(root)
    slots, slot_err = build_plan_review_slots(config)
    if slot_err:
        raise ValueError(slot_err)

    reviewer_labels = getattr(args, "reviewer_labels", None)
    if reviewer_labels:
        wanted = frozenset(reviewer_labels)
        slots = [s for s in slots if s.label in wanted]
        if not slots:
            raise ValueError(
                "no reviewers match --reviewer (labels are exact): " + ", ".join(sorted(wanted))
            )

    prompt_path = root / ".onward/prompts/review-plan.md"
    if prompt_path.exists():
        prompt = prompt_path.read_text(encoding="utf-8")
    else:
        prompt = "Review this plan for gaps, security issues, missing requirements, and deployment risks."

    plan_id = str(plan.metadata.get("id", ""))
    review_paths: list[Path] = []

    for slot in slots:
        n_tries = len(slot.tries)
        print(f"Running review: {slot.label}...")
        ok_slot = False
        review_path: Path | None = None
        for try_idx, tri in enumerate(slot.tries, start=1):
            print(
                f"review-plan: slot={slot.label} try={try_idx}/{n_tries} "
                f"model={tri.model_resolved} executor={tri.executor}"
            )
            pre_err = preflight_shell_invocation(tri.executor)
            if pre_err:
                print(
                    f"review-plan: slot={slot.label} fallback_reason=preflight_failed "
                    f"try={try_idx}/{n_tries} model={tri.model_resolved} executor={tri.executor} "
                    f"detail={pre_err}"
                )
                continue
            is_last = try_idx == n_tries
            ok, review_path = execute_plan_review(
                root,
                plan,
                tri.model_resolved,
                slot.label,
                prompt,
                executor_command=tri.executor,
                executor_args=list(tri.executor_args),
                emit_errors=is_last,
            )
            if ok:
                ok_slot = True
                break
            print(
                f"review-plan: slot={slot.label} fallback_reason=executor_failed "
                f"try={try_idx}/{n_tries} model={tri.model_resolved} executor={tri.executor}"
            )
        if ok_slot and review_path is not None:
            review_paths.append(review_path)
            print(f"  -> {review_path.relative_to(root)}")
        else:
            print(f"  -> Review {slot.label} failed.")

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
    artifact = must_find_by_id(root, args.id)
    artifact_type = str(artifact.metadata.get("type", ""))
    if artifact_type == "task":
        ok, run_id = work_task(root, artifact)
        if run_id:
            print(f"Run {run_id}: {'completed' if ok else 'failed'}")
        else:
            print(f"{args.id} already completed")
        if ok:
            _, warnings = finalize_chunks_all_tasks_terminal(root)
            for w in warnings:
                print(w)
        return 0 if ok else 1
    if artifact_type != "chunk":
        raise ValueError(f"{args.id} is not a task or chunk")

    chunk = artifact
    chunk_id = str(chunk.metadata.get("id", ""))
    if str(chunk.metadata.get("status", "")) == "completed":
        print(f"Chunk {chunk_id} already completed")
        return 0
    config = load_workspace_config(root)
    sequential = work_sequential_by_default(config)
    if str(chunk.metadata.get("status", "")) in {"open", "in_progress"}:
        update_artifact_status(root, chunk, "in_progress")

    while True:
        ready_tasks, all_resolved = ordered_ready_chunk_tasks(root, chunk_id)
        if not ready_tasks:
            if not all_resolved:
                print(f"Chunk {chunk_id} has unresolved task dependencies")
                return 1
            break
        next_task = ready_tasks[0]
        ok, run_id = work_task(root, next_task)
        print(f"Run {run_id}: {'completed' if ok else 'failed'}")
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


def cmd_split(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifact = must_find_by_id(root, args.id)
    artifact_type = str(artifact.metadata.get("type", ""))
    if artifact_type not in {"plan", "chunk"}:
        raise ValueError(f"{args.id} is not splittable (expected PLAN-* or CHUNK-*)")

    config = load_workspace_config(root)
    default_model = model_setting(config, "default", "opus-latest")
    split_model = clean_string(args.model) or model_setting(config, "split_default", "") or default_model
    task_default_model = model_setting(config, "task_default", "sonnet-latest")

    prompt_name = "split-plan.md" if artifact_type == "plan" else "split-chunk.md"
    raw = run_split_model(artifact, prompt_name, split_model, task_default_model)

    if artifact_type == "plan":
        parsed = parse_split_payload(raw, "chunks")
        normalized = normalize_chunk_candidates(parsed, default_model)
        writes = prepare_chunk_writes(root, artifact, normalized)
    else:
        parsed = parse_split_payload(raw, "tasks")
        normalized = normalize_task_candidates(parsed, task_default_model)
        writes = prepare_task_writes(root, artifact, normalized)

    assert_writes_safe(root, writes)

    if args.dry_run:
        split_kind = "plan→chunks" if artifact_type == "plan" else "chunk→tasks"
        child_type = "CHUNK" if artifact_type == "plan" else "TASK"
        print(f"Split dry-run ({split_kind}) for {args.id} using model={split_model}")
        print(f"Prompt: .onward/prompts/{prompt_name}")
        for artifact_id, path, _content in writes:
            print(f"{child_type}: create {artifact_id}\t{path.relative_to(root)}")
        return 0

    for _artifact_id, path, content in writes:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    regenerate_indexes(root)

    for artifact_id, path, _content in writes:
        print(f"Created {artifact_id} at {path.relative_to(root)}")
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    rows: list[str] = []

    for artifact in collect_artifacts(root):
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
        ongoing = load_ongoing(root)
        active = ongoing.get("active_runs", [])
        if not isinstance(active, list) or not active:
            print("No in-progress artifacts")
            return 0
    else:
        for row in sorted(rows):
            print(row)

    ongoing = load_ongoing(root)
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

    for artifact in collect_artifacts(root):
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

    for rec in collect_run_records(root):
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
    _, warnings = finalize_chunks_all_tasks_terminal(root)
    for w in warnings:
        print(w)
    artifacts = collect_artifacts(root)
    chosen = select_next_artifact(artifacts, project=(args.project or "").strip() or None)
    if chosen:
        print(
            f"{chosen.metadata.get('id')}\t{chosen.metadata.get('type')}\t{chosen.metadata.get('status')}\t{chosen.metadata.get('title')}\t{chosen.file_path.relative_to(root)}"
        )
        return 0

    print("No next artifact found")
    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifacts = collect_artifacts(root)
    project = (args.project or "").strip() or None
    lines = render_active_work_tree_lines(artifacts, root, project=project, color_enabled=not args.no_color)
    if not lines:
        print("No active work tree (no open plans)")
        return 0
    for line in lines:
        print(line)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    color_enabled = not args.no_color
    project = (args.project or "").strip() or None
    _, warnings = finalize_chunks_all_tasks_terminal(root)
    for w in warnings:
        print(w)
    artifacts = collect_artifacts(root)
    blockers = blocking_ids(artifacts)
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts}

    print(colorize("== Onward Report ==", "bold", color_enabled))
    if project:
        print(f"project: {project}")
    print()

    print(colorize("[In Progress]", "cyan", color_enabled))
    in_progress = report_rows(artifacts, root, status="in_progress", project=project)
    if in_progress:
        for row in in_progress:
            parts = row.split("\t")
            parts[2] = colorize(parts[2], status_color(parts[2]), color_enabled)
            print("\t".join(parts))
    else:
        print("none")
    print()

    print(colorize("[Next]", "cyan", color_enabled))
    nxt = select_next_artifact(artifacts, project=project)
    if nxt:
        status = str(nxt.metadata.get("status", ""))
        print(
            "\t".join(
                [
                    str(nxt.metadata.get("id", "")),
                    str(nxt.metadata.get("type", "")),
                    colorize(status, status_color(status), color_enabled),
                    str(nxt.metadata.get("title", "")),
                    str(nxt.file_path.relative_to(root)),
                ]
            )
        )
    else:
        print("none")
    print()

    print(colorize("[Blocking Human Tasks]", "cyan", color_enabled))
    human_blockers: list[str] = []
    for blocker_id in sorted(blockers):
        artifact = by_id.get(blocker_id)
        if not artifact:
            continue
        if project and artifact_project(artifact) != project:
            continue
        if not is_human_task(artifact):
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

    print(colorize("[Recent Completed]", "cyan", color_enabled))
    completed = [
        a
        for a in artifacts
        if str(a.metadata.get("status", "")) == "completed"
        and (not project or artifact_project(a) == project)
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
                        colorize(status, status_color(status), color_enabled),
                        str(artifact.metadata.get("title", "")),
                    ]
                )
            )
    else:
        print("none")
    print()

    print(colorize("[Active work tree]", "cyan", color_enabled))
    tree_lines = render_active_work_tree_lines(artifacts, root, project=project, color_enabled=color_enabled)
    if not tree_lines:
        print("none")
        return 0
    for line in tree_lines:
        print(line)
    return 0

