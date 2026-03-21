"""Onward CLI command implementations (parser and entrypoint live in onward.cli)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from onward.artifacts import (
    Artifact,
    append_note,
    artifact_glob,
    artifact_project,
    artifacts_from_index_or_collect,
    blocking_ids,
    collect_artifacts,
    create_follow_up_tasks,
    find_by_id,
    find_dependents,
    find_plan_dir,
    format_artifact,
    is_human_task,
    list_from_index,
    must_find_by_id,
    next_id,
    next_ids,
    parse_artifact,
    read_notes,
    regenerate_indexes,
    render_active_work_tree_lines,
    report_rows,
    resolve_project,
    select_next_artifact,
    summarize_effort_remaining,
    task_is_next_actionable,
    transition_status,
    update_artifact_status,
    validate_artifact,
    write_artifact,
)
from onward.config import (
    build_plan_review_slots,
    config_raw_deprecation_warnings,
    config_validation_warnings,
    load_artifact_template,
    load_workspace_config,
    model_setting,
    validate_config_contract_issues,
)
from onward.preflight import preflight_shell_invocation
from onward.execution import (
    collect_run_records,
    collect_runs_for_target,
    execute_plan_review,
    finalize_chunks_all_tasks_terminal,
    load_ongoing,
    work_chunk,
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
    validate_split_output,
)
from onward.util import (
    as_str_list,
    clean_string,
    colorize,
    dump_simple_yaml,
    normalize_acceptance,
    normalize_bool,
    normalize_effort,
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
    for w in config_validation_warnings(config):
        print(f"Warning: {w}")
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
    blocked_by_warnings: list[str] = []
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

        if as_str_list(artifact.metadata.get("blocked_by")):
            blocked_by_warnings.append(
                f"{artifact.file_path.relative_to(root)}: 'blocked_by' is deprecated; use 'depends_on' instead"
            )

    for msg in blocked_by_warnings:
        print(f"Warning: {msg}")

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
        "project": "" if args.project is None else args.project,
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

    plan_art = find_by_id(root, plan_id)
    if not plan_art:
        raise ValueError(f"plan not found: {plan_id}")
    if str(plan_art.metadata.get("type", "")) != "plan":
        raise ValueError(f"{plan_id} is not a plan")

    plan_dir = find_plan_dir(root, plan_id)
    chunk_id = next_id(root, "CHUNK")
    now = now_iso()
    slug = slugify(args.title)

    if args.project is None:
        proj = artifact_project(plan_art)
    else:
        proj = args.project

    metadata = {
        "id": chunk_id,
        "type": "chunk",
        "plan": plan_id,
        "project": proj,
        "title": args.title,
        "status": "open",
        "description": args.description or "",
        "priority": args.priority,
        "model": args.model,
        "created_at": now,
        "updated_at": now,
    }
    raw_eff = getattr(args, "effort", None)
    if raw_eff is not None and str(raw_eff).strip():
        eff = normalize_effort(raw_eff)
        if eff:
            metadata["effort"] = eff
        else:
            print("Warning: invalid --effort value (expected xs|s|m|l|xl); leaving unset")
    if getattr(args, "estimated_files", None) is not None:
        metadata["estimated_files"] = int(args.estimated_files)

    body = load_artifact_template(root, "chunk")
    target = plan_dir / "chunks" / f"{chunk_id}-{slug}.md"
    target.write_text(format_artifact(metadata, body), encoding="utf-8")

    regenerate_indexes(root)
    print(f"Created {chunk_id} at {target.relative_to(root)}")
    return 0


_BATCH_DEP_INDEX = re.compile(r"^\$(\d+)$")


def cmd_new_task_batch(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    chunk = find_by_id(root, args.chunk_id)
    if not chunk:
        raise ValueError(f"chunk not found: {args.chunk_id}")
    if str(chunk.metadata.get("type", "")) != "chunk":
        raise ValueError(f"{args.chunk_id} is not a chunk")

    plan_id = str(chunk.metadata["plan"])
    chunk_id = str(chunk.metadata["id"])
    plan_dir = find_plan_dir(root, plan_id)

    batch_path = Path(args.batch).expanduser()
    if not batch_path.is_file():
        raise ValueError(f"batch file not found: {batch_path}")
    try:
        raw = json.loads(batch_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in batch file: {exc}") from exc
    if not isinstance(raw, list):
        raise ValueError("batch file must contain a JSON array")
    if len(raw) == 0:
        raise ValueError("batch array is empty")

    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"batch entry {i} must be a JSON object")
        title = clean_string(entry.get("title", ""))
        desc = clean_string(entry.get("description", ""))
        if not title or not desc:
            raise ValueError(f"batch entry {i} must have non-empty title and description")

    task_ids = next_ids(root, "TASK", len(raw))

    if args.project is None:
        base_project = artifact_project(chunk)
    else:
        base_project = args.project

    body_template = load_artifact_template(root, "task")
    writes: list[tuple[str, Path, str]] = []

    for i, entry in enumerate(raw):
        assert isinstance(entry, dict)
        title = clean_string(entry.get("title", ""))
        desc = clean_string(entry.get("description", ""))
        model = clean_string(entry.get("model", "")) or "sonnet-latest"
        human = normalize_bool(entry.get("human", False))

        deps_in = entry.get("depends_on") or []
        if not isinstance(deps_in, list):
            raise ValueError(f"batch entry {i}: depends_on must be a list")
        dep_ids: list[str] = []
        for dep in deps_in:
            ds = str(dep).strip()
            if not ds:
                continue
            m = _BATCH_DEP_INDEX.match(ds)
            if m:
                j = int(m.group(1))
                if j < 0 or j >= len(raw):
                    raise ValueError(f"batch entry {i}: invalid intra-batch reference {ds!r}")
                dep_ids.append(task_ids[j])
            else:
                dep_ids.append(ds)
        seen_d: set[str] = set()
        dep_ids = [d for d in dep_ids if d not in seen_d and not seen_d.add(d)]

        files = entry.get("files") or []
        if not isinstance(files, list):
            raise ValueError(f"batch entry {i}: files must be a list")
        file_list = [str(x).strip() for x in files if str(x).strip()]

        acc = entry.get("acceptance") or []
        if isinstance(acc, list):
            acceptance = [str(x).strip() for x in acc if str(x).strip()]
        else:
            acceptance = normalize_acceptance(acc)

        tid = task_ids[i]
        now = now_iso()
        metadata: dict[str, Any] = {
            "id": tid,
            "type": "task",
            "plan": plan_id,
            "chunk": chunk_id,
            "project": base_project,
            "title": title,
            "status": "open",
            "description": desc,
            "human": human,
            "model": model,
            "executor": "onward-exec",
            "depends_on": dep_ids,
            "files": file_list,
            "acceptance": acceptance,
            "created_at": now,
            "updated_at": now,
        }
        eff = normalize_effort(entry.get("effort", ""))
        if eff:
            metadata["effort"] = eff

        slug = slugify(title)
        target = plan_dir / "tasks" / f"{tid}-{slug}.md"
        writes.append((tid, target, format_artifact(metadata, body_template)))

    if args.dry_run:
        for tid, path, _ in writes:
            print(f"dry-run: would create {tid}\t{path.relative_to(root)}")
        return 0

    for _tid, path, content in writes:
        path.write_text(content, encoding="utf-8")
    regenerate_indexes(root)
    for tid, path, _ in writes:
        print(f"Created {tid} at {path.relative_to(root)}")
    return 0


def cmd_new_task(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if getattr(args, "batch", None):
        return cmd_new_task_batch(args)

    if not args.title:
        raise ValueError("task title is required unless --batch is used")

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
    if args.project is None:
        proj = artifact_project(chunk)
    else:
        proj = args.project

    metadata = {
        "id": task_id,
        "type": "task",
        "plan": plan_id,
        "chunk": chunk_id,
        "project": proj,
        "title": args.title,
        "status": "open",
        "description": args.description or "",
        "human": bool(args.human),
        "model": args.model,
        "executor": "onward-exec",
        "depends_on": [],
        "files": [],
        "acceptance": [],
        "created_at": now,
        "updated_at": now,
    }
    raw_eff = getattr(args, "effort", None)
    if raw_eff is not None and str(raw_eff).strip():
        eff = normalize_effort(raw_eff)
        if eff:
            metadata["effort"] = eff
        else:
            print("Warning: invalid --effort value (expected xs|s|m|l|xl); leaving unset")

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

    indexed = list_from_index(
        root,
        type_filter=artifact_type,
        project_filter=project_filter,
        blocking=blockers_only,
        human_only=human_only,
    )
    if indexed is not None:
        rows = indexed
    else:
        artifacts = collect_artifacts(root)
        blocker_ids = blocking_ids(artifacts) if blockers_only else set()
        by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}

        rows = []
        for artifact in artifacts:
            m = artifact.metadata
            row_type = str(m.get("type", ""))
            if artifact_type != "all" and row_type != artifact_type:
                continue
            if project_filter and resolve_project(artifact, by_id) != project_filter:
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
                    "project": resolve_project(artifact, by_id),
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


def _print_task_show_extras(root: Path, artifact: Artifact) -> None:
    """Extra sections for ``onward show TASK-*`` (run history, structured result, deps)."""
    tty = sys.stdout.isatty()
    artifact_id = str(artifact.metadata.get("id", ""))

    rc = artifact.metadata.get("run_count")
    lrs = artifact.metadata.get("last_run_status")
    if rc is not None or lrs is not None:
        print()
        print("Retry / execution:")
        if rc is not None:
            print(f"  run_count: {rc}")
        if lrs is not None:
            ls = str(lrs)
            print(f"  last_run_status: {colorize(ls, status_color(ls), tty)}")

    runs = collect_runs_for_target(root, artifact_id, limit=10)
    print()
    print("Run history:")
    if not runs:
        print("  (no runs recorded)")
    else:
        for r in runs:
            rid = str(r.get("id", ""))
            st = str(r.get("status", ""))
            st_disp = colorize(st, status_color(st), tty)
            print(f"  {rid}  {st_disp}  started={r.get('started_at')}  finished={r.get('finished_at')}")
            print(f"    log: {r.get('log_path')}")

    last_result: dict[str, Any] | None = None
    for r in runs:
        if str(r.get("status", "")) != "completed":
            continue
        tr = r.get("task_result")
        if isinstance(tr, dict) and tr:
            last_result = tr
            break

    print()
    print("Last result:")
    if not last_result:
        print("  (no structured result on completed runs)")
    else:
        summ = (last_result.get("summary") or "").strip()
        if summ:
            print(f"  summary: {summ}")
        files = last_result.get("files_changed") or []
        if files:
            print("  files_changed:")
            for fpath in files:
                print(f"    - {fpath}")
        am = last_result.get("acceptance_met") or []
        if am:
            print("  acceptance_met:")
            for line in am:
                print(f"    - {line}")
        au = last_result.get("acceptance_unmet") or []
        if au:
            print("  acceptance_unmet:")
            for line in au:
                print(f"    - {line}")
        fus = last_result.get("follow_ups") or []
        if fus:
            print("  follow_ups:")
            for fu in fus:
                if isinstance(fu, dict):
                    print(f"    - {fu.get('title', '')}: {fu.get('description', '')}")

    artifacts = collect_artifacts(root)
    status_by_id = {
        str(a.metadata.get("id", "")): str(a.metadata.get("status", "")) for a in artifacts
    }

    deps = as_str_list(artifact.metadata.get("depends_on")) + as_str_list(
        artifact.metadata.get("blocked_by")
    )
    print()
    print("Dependencies:")
    if not deps:
        print("  (none)")
    else:
        for dep_id in deps:
            st = status_by_id.get(dep_id, "?")
            print(f"  {dep_id}  [{colorize(st, status_color(st), tty)}]")

    dependents = find_dependents(artifacts, artifact_id)
    print()
    print("Blocked tasks:")
    if not dependents:
        print("  (none)")
    else:
        for d in dependents:
            did = str(d.metadata.get("id", ""))
            st = str(d.metadata.get("status", ""))
            print(
                f"  {did}  [{colorize(st, status_color(st), tty)}]  {d.metadata.get('title', '')}"
            )


def cmd_show(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifact = find_by_id(root, args.id)
    if not artifact:
        print(f"Artifact not found: {args.id}")
        return 1

    project = (getattr(args, "project", "") or "").strip()
    if project:
        artifacts = collect_artifacts(root)
        by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
        if resolve_project(artifact, by_id) != project:
            print(f"Artifact not in project {project!r} (resolved)")
            return 1

    print(f"# {artifact.metadata.get('id')} {artifact.metadata.get('title')}")
    print(f"type: {artifact.metadata.get('type')}")
    print(f"status: {artifact.metadata.get('status')}")
    eff = str(artifact.metadata.get("effort", "")).strip()
    if eff:
        print(f"effort: {eff}")
    print(f"path: {artifact.file_path.relative_to(root)}")
    print()
    print(dump_simple_yaml(artifact.metadata).rstrip())
    print("---")
    print(artifact.body.rstrip())

    if str(artifact.metadata.get("type", "")) == "task":
        _print_task_show_extras(root, artifact)
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


def cmd_complete(args: argparse.Namespace) -> int:
    return _cmd_set_status(args, "complete")


def cmd_cancel(args: argparse.Namespace) -> int:
    return _cmd_set_status(args, "cancel")


def cmd_retry(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    artifact = must_find_by_id(root, args.id)
    if str(artifact.metadata.get("type", "")) != "task":
        raise ValueError("onward retry only applies to tasks (TASK-###)")
    current = str(artifact.metadata.get("status", ""))
    artifact.metadata["status"] = transition_status(current, "retry")
    artifact.metadata["run_count"] = 0
    artifact.metadata["updated_at"] = now_iso()
    write_artifact(artifact)
    regenerate_indexes(root)
    artifact_id = str(artifact.metadata.get("id", ""))
    print(f"{artifact_id} status: {current} -> {artifact.metadata.get('status')}")
    return 0


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
                f"model={tri.model} executor={tri.executor}"
            )
            pre_err = preflight_shell_invocation(tri.executor)
            if pre_err:
                print(
                    f"review-plan: slot={slot.label} fallback_reason=preflight_failed "
                    f"try={try_idx}/{n_tries} model={tri.model} executor={tri.executor} "
                    f"detail={pre_err}"
                )
                continue
            is_last = try_idx == n_tries
            ok, review_path = execute_plan_review(
                root,
                plan,
                tri.model,
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
                f"try={try_idx}/{n_tries} model={tri.model} executor={tri.executor}"
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


def _status_by_id(root: Path) -> dict[str, str]:
    return {
        str(a.metadata.get("id", "")): str(a.metadata.get("status", ""))
        for a in collect_artifacts(root)
        if str(a.metadata.get("id", ""))
    }


def _chunk_depends_satisfied(chunk: Artifact, status_by_id: dict[str, str]) -> bool:
    for dep in as_str_list(chunk.metadata.get("depends_on")):
        if status_by_id.get(dep) != "completed":
            return False
    return True


def _plan_chunks(root: Path, plan_id: str) -> list[Artifact]:
    chunks = [
        a
        for a in collect_artifacts(root)
        if str(a.metadata.get("type", "")) == "chunk"
        and str(a.metadata.get("plan", "")) == plan_id
    ]
    return sorted(chunks, key=lambda a: str(a.metadata.get("id", "")))


def _work_chunk(root: Path, chunk: Artifact, config: dict[str, Any]) -> int:
    return work_chunk(root, chunk, config)


def _work_plan(root: Path, plan: Artifact, config: dict[str, Any]) -> int:
    plan_id = str(plan.metadata.get("id", ""))
    st = str(plan.metadata.get("status", ""))
    if st == "completed":
        print(f"Plan {plan_id} already completed")
        return 0

    chunks = _plan_chunks(root, plan_id)
    if not chunks:
        print(f"Plan {plan_id} has no chunks")
        return 0

    if st in {"open", "in_progress"}:
        update_artifact_status(root, plan, "in_progress")

    pending = [
        str(c.metadata.get("id", ""))
        for c in chunks
        if str(c.metadata.get("status", "")) not in {"completed", "canceled"}
    ]
    if not pending:
        refreshed_plan = must_find_by_id(root, plan_id)
        update_artifact_status(root, refreshed_plan, "completed")
        _, warnings = finalize_chunks_all_tasks_terminal(root)
        for w in warnings:
            print(w)
        n_tasks = sum(
            1
            for a in collect_artifacts(root)
            if str(a.metadata.get("type", "")) == "task"
            and str(a.metadata.get("plan", "")) == plan_id
            and str(a.metadata.get("status", "")) == "completed"
        )
        print(f"Plan {plan_id} completed ({len(chunks)} chunks, {n_tasks} tasks)")
        return 0

    while pending:
        status_by_id = _status_by_id(root)
        ready = [
            cid
            for cid in pending
            if _chunk_depends_satisfied(must_find_by_id(root, cid), status_by_id)
        ]
        if not ready:
            print(
                f"Plan {plan_id}: no chunk is ready to run (check chunk depends_on / ordering)"
            )
            return 1
        cid = min(ready)
        chunk_art = must_find_by_id(root, cid)
        code = _work_chunk(root, chunk_art, config)
        if code != 0:
            print(f"Stopping plan work for {plan_id} after chunk {cid} failure")
            return 1
        pending.remove(cid)

    refreshed_plan = must_find_by_id(root, plan_id)
    update_artifact_status(root, refreshed_plan, "completed")
    _, warnings = finalize_chunks_all_tasks_terminal(root)
    for w in warnings:
        print(w)
    n_tasks = sum(
        1
        for a in collect_artifacts(root)
        if str(a.metadata.get("type", "")) == "task"
        and str(a.metadata.get("plan", "")) == plan_id
        and str(a.metadata.get("status", "")) == "completed"
    )
    print(f"Plan {plan_id} completed ({len(chunks)} chunks, {n_tasks} tasks)")
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
        if ok and run_id and not getattr(args, "no_follow_ups", False):
            run_path = root / ".onward/runs" / f"{run_id}.json"
            if run_path.exists():
                try:
                    rec = json.loads(run_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    rec = {}
                tr = rec.get("task_result") or {}
                fus = tr.get("follow_ups") or []
                if isinstance(fus, list) and fus:
                    parent = must_find_by_id(root, args.id)
                    created, fu_warnings = create_follow_up_tasks(root, parent, fus)
                    for w in fu_warnings:
                        print(f"Warning: {w}")
                    for cid in created:
                        print(f"Created follow-up task {cid}")
        if ok:
            _, warnings = finalize_chunks_all_tasks_terminal(root)
            for w in warnings:
                print(w)
        return 0 if ok else 1
    config = load_workspace_config(root)
    if artifact_type == "plan":
        return _work_plan(root, artifact, config)
    if artifact_type != "chunk":
        raise ValueError(f"{args.id} is not a task, chunk, or plan")
    return _work_chunk(root, artifact, config)


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
    raw = run_split_model(
        root,
        artifact,
        prompt_name,
        split_model,
        task_default_model,
        heuristic=bool(getattr(args, "heuristic", False)),
        config=config,
    )

    if artifact_type == "plan":
        parsed = parse_split_payload(raw, "chunks")
        normalized = normalize_chunk_candidates(parsed, default_model)
        writes = prepare_chunk_writes(root, artifact, normalized)
        split_kind = "plan"
    else:
        parsed = parse_split_payload(raw, "tasks")
        normalized = normalize_task_candidates(parsed, task_default_model)
        writes = prepare_task_writes(root, artifact, normalized)
        split_kind = "chunk"

    warnings, val_errors = validate_split_output(normalized, split_kind)
    force = bool(getattr(args, "force", False))
    for w in warnings:
        print(f"Warning: {w}")
    for e in val_errors:
        if args.dry_run:
            print(f"Error: {e}")
        elif force:
            print(f"Warning: {e} (ignored with --force)")
        else:
            print(f"Error: {e}")
    if not args.dry_run and val_errors and not force:
        return 1

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
    project = (getattr(args, "project", "") or "").strip()
    artifacts = collect_artifacts(root)
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
    rows: list[str] = []

    for artifact in artifacts:
        status = str(artifact.metadata.get("status", ""))
        if status != "in_progress":
            continue
        if project and resolve_project(artifact, by_id) != project:
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
    project = (getattr(args, "project", "") or "").strip()
    artifacts = collect_artifacts(root)
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
    rows: list[tuple[str, str, str, str, str, str]] = []

    for artifact in artifacts:
        status = str(artifact.metadata.get("status", ""))
        if status != "completed":
            continue
        if project and resolve_project(artifact, by_id) != project:
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
        if project:
            targ_art = by_id.get(target)
            if targ_art is None or resolve_project(targ_art, by_id) != project:
                continue
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


def cmd_ready(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    _, warnings = finalize_chunks_all_tasks_terminal(root)
    for w in warnings:
        print(w)
    artifacts = artifacts_from_index_or_collect(root)
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
    project = (args.project or "").strip() or None
    status_by_id = {
        str(a.metadata.get("id", "")): str(a.metadata.get("status", ""))
        for a in artifacts
        if a.metadata.get("id")
    }
    ready_tasks = [
        a
        for a in artifacts
        if str(a.metadata.get("type", "")) == "task" and task_is_next_actionable(a, status_by_id)
    ]
    if project:
        ready_tasks = [a for a in ready_tasks if resolve_project(a, by_id) == project]
    ready_tasks.sort(key=lambda a: str(a.metadata.get("id", "")))
    if not ready_tasks:
        print("No ready tasks")
        return 0

    plans_by_id = {str(a.metadata.get("id", "")): a for a in artifacts if str(a.metadata.get("type", "")) == "plan"}
    chunks_by_id = {str(a.metadata.get("id", "")): a for a in artifacts if str(a.metadata.get("type", "")) == "chunk"}
    tty = not args.no_color

    grouped: dict[str, dict[str, list[Artifact]]] = defaultdict(lambda: defaultdict(list))
    for t in ready_tasks:
        pid = str(t.metadata.get("plan", ""))
        cid = str(t.metadata.get("chunk", ""))
        grouped[pid][cid].append(t)

    for pid in sorted(grouped.keys()):
        plan = plans_by_id.get(pid)
        ptitle = plan.metadata.get("title", pid) if plan else pid
        print(f"{pid} {ptitle}")
        for cid in sorted(grouped[pid].keys()):
            chunk = chunks_by_id.get(cid)
            ctitle = str(chunk.metadata.get("title", cid)) if chunk else cid
            cst = str(chunk.metadata.get("status", "")) if chunk else ""
            cst_disp = colorize(cst, status_color(cst), tty) if cst else ""
            print(f"  {cid} [{cst_disp}] {ctitle}")
            for task in sorted(grouped[pid][cid], key=lambda a: str(a.metadata.get("id", ""))):
                marker = "H" if is_human_task(task) else "A"
                tid = str(task.metadata.get("id", ""))
                ttitle = str(task.metadata.get("title", ""))
                eff = str(task.metadata.get("effort", "")).strip()
                eff_s = f" [{eff}]" if eff else ""
                print(f"    {tid} ({marker}) {ttitle}{eff_s}")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    _, warnings = finalize_chunks_all_tasks_terminal(root)
    for w in warnings:
        print(w)
    artifacts = artifacts_from_index_or_collect(root)
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
    artifacts = artifacts_from_index_or_collect(root)
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
    artifacts = artifacts_from_index_or_collect(root)
    blockers = blocking_ids(artifacts)
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts}

    print(colorize("== Onward Report ==", "bold", color_enabled))
    if project:
        print(f"project: {project}")
    print()

    print(colorize("[Effort remaining]", "cyan", color_enabled))
    eff_counts = summarize_effort_remaining(artifacts)
    print(
        "  "
        + "  ".join(
            f"{k}: {eff_counts[k]}"
            for k in ("xs", "s", "m", "l", "xl", "unestimated")
        )
    )
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

    print(colorize("[Upcoming]", "cyan", color_enabled))
    upcoming = report_rows(artifacts, root, status="open", project=project)
    if upcoming:
        for row in upcoming:
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
        if project and resolve_project(artifact, by_id) != project:
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
        and (not project or resolve_project(a, by_id) == project)
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

