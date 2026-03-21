"""Onward CLI command implementations (parser and entrypoint live in onward.cli)."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
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
    claimed_rows,
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
    WorkspaceLayout,
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
    chunk_has_nonterminal_tasks,
    register_claim,
    release_claim,
    claimed_task_ids,
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
    default_directories,
    default_files,
    gitignore_lines,
    require_workspace,
    required_paths,
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
    run_timestamp,
    slugify,
    split_frontmatter,
    status_color,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def require_project_or_default(args: argparse.Namespace, layout: WorkspaceLayout, *, enforce: bool = True) -> str | None:
    """Resolve project key from args or config default, optionally enforcing multi-root requirements.

    Args:
        args: Parsed CLI arguments (must have a `project` attribute)
        layout: WorkspaceLayout instance for this workspace
        enforce: If True, raise error in multi-root mode when no project is available.
                 If False, return None when no project is specified (allows searching all roots).

    Returns:
        Project key string (in multi-root mode) or None (in single-root mode or when not enforced)

    Raises:
        ValueError: If enforce=True and multi-root mode is active but no project is specified and no default_project is set
        ValueError: If the specified project is not in the configured roots
    """
    # Single-root mode: always return None (project is optional metadata filter)
    if not layout.is_multi_root:
        return None

    # Multi-root mode: resolve project from args or default_project
    project = getattr(args, "project", None)
    if project is not None:
        # Empty string from CLI is treated as None (user didn't specify)
        project = project.strip() or None

    if project is None:
        # Try to use default_project from config
        if layout.default_project is not None:
            project = layout.default_project
        elif enforce:
            # No project specified and no default: error (only if enforcing)
            available = [k for k in layout.roots.keys() if k is not None]
            raise ValueError(
                f"Multiple project roots configured. Use --project <name> or set default_project in .onward.config.yaml. "
                f"Available projects: {', '.join(sorted(available))}"
            )
        else:
            # Not enforcing: return None (will search all roots)
            return None

    # Validate that the project exists in the configured roots
    if project is not None and project not in layout.roots:
        available = [k for k in layout.roots.keys() if k is not None]
        raise ValueError(
            f"Unknown project {project!r}. Available projects: {', '.join(sorted(available))}"
        )

    return project


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()

    # Load config if it exists, otherwise use empty dict (defaults to .onward)
    config_path = root / ".onward.config.yaml"
    config = {}
    if config_path.exists():
        raw = parse_simple_yaml(config_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            config = raw

    # Build layout from config
    layout = WorkspaceLayout.from_config(root, config)

    # Always ensure the config file exists at workspace root
    config_content = default_files(".onward")[".onward.config.yaml"]
    config_wrote = write_workspace_file(config_path, config_content, force=args.force)

    created = 0
    if config_wrote:
        created += 1

    # Scaffold each artifact root
    artifact_roots_scaffolded = []
    for project_key in layout.all_project_keys():
        artifact_root = layout.artifact_root(project_key)
        # Convert to path relative to workspace root for scaffold functions
        artifact_root_rel = artifact_root.relative_to(root)
        artifact_root_str = str(artifact_root_rel)

        # Create directories
        for rel_path in default_directories(artifact_root_str):
            (root / rel_path).mkdir(parents=True, exist_ok=True)

        # Create artifact-relative files (skip config file as we already wrote it)
        for rel_path, content in default_files(artifact_root_str).items():
            if rel_path == ".onward.config.yaml":
                continue  # Already written above
            wrote = write_workspace_file(root / rel_path, content, force=args.force)
            if wrote:
                created += 1

        artifact_roots_scaffolded.append(artifact_root_str)

    # Update gitignore with all artifact roots
    gitignore_updated = False
    for artifact_root_str in artifact_roots_scaffolded:
        if update_gitignore(root, artifact_root=artifact_root_str):
            gitignore_updated = True

    # Note: regenerate_indexes() is not called here because it still uses hardcoded .onward paths
    # and hasn't been updated for multi-root support yet (CHUNK-005). The index files are already
    # created with default empty content by default_files(), which is sufficient for initialization.

    print(f"Initialized Onward workspace in {root}")
    if artifact_roots_scaffolded:
        print(f"Artifact roots: {', '.join(artifact_roots_scaffolded)}")
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

    # Build layout to determine artifact root(s)
    layout = WorkspaceLayout.from_config(root, config)

    # Check each configured project root
    for project_key in layout.all_project_keys():
        try:
            artifact_root_path = layout.artifact_root(project_key)
        except ValueError as exc:
            # Should not happen since we're iterating over known keys, but handle gracefully
            issues.append(str(exc))
            continue

        # Compute relative artifact root for display
        artifact_root_rel = artifact_root_path.relative_to(root) if artifact_root_path.is_relative_to(root) else artifact_root_path
        artifact_root_str = str(artifact_root_rel)

        # Label for multi-root mode
        project_label = f" [{project_key}]" if layout.is_multi_root and project_key else ""

        # Check artifact root directory exists
        if not artifact_root_path.exists():
            issues.append(f"missing artifact root{project_label}: {artifact_root_str}/")
            continue  # Skip subdirectory checks if root doesn't exist

        # Check required subdirectories exist
        required_subdirs = [
            "plans",
            "plans/.archive",
            "templates",
            "prompts",
            "hooks",
            "sync",
            "runs",
            "reviews",
            "notes",
        ]
        for subdir in required_subdirs:
            subdir_path = artifact_root_path / subdir
            if not subdir_path.exists():
                issues.append(f"missing directory{project_label}: {artifact_root_str}/{subdir}/")

        # Check required files under this artifact root
        for rel_path in required_paths(artifact_root_str):
            path = root / rel_path
            if not path.exists():
                issues.append(f"missing required file{project_label}: {rel_path}")

        # Check ongoing.json validity if it exists
        ongoing_path = layout.ongoing_path(project_key)
        if ongoing_path.exists():
            try:
                json.loads(ongoing_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                ongoing_rel = ongoing_path.relative_to(root) if ongoing_path.is_relative_to(root) else ongoing_path
                issues.append(f"invalid json{project_label} in {ongoing_rel}: {exc}")

        # Check .gitignore entries for this artifact root
        gitignore_path = root / ".gitignore"
        if not gitignore_path.exists():
            if not layout.is_multi_root or project_key == layout.all_project_keys()[0]:
                # Only report once for missing .gitignore
                issues.append("missing .gitignore")
        else:
            lines = set(gitignore_path.read_text(encoding="utf-8").splitlines())
            for entry in gitignore_lines(artifact_root_str):
                if entry not in lines:
                    issues.append(f"missing .gitignore entry{project_label}: {entry}")

    seen_ids: set[str] = set()
    blocked_by_warnings: list[str] = []
    for path in artifact_glob(layout):
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


def cmd_migrate(args: argparse.Namespace) -> int:
    """Migrate artifacts from old root to new configured root."""
    root = Path(args.root).resolve()
    dry_run = args.dry_run
    force = args.force
    project_arg = args.project if args.project else None

    # Load config and create layout
    config_path = root / ".onward.config.yaml"
    if not config_path.exists():
        print("Error: .onward.config.yaml not found. Initialize workspace first with 'onward init'")
        return 1

    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)

    # Determine which project root to migrate to
    target_project_key = project_arg
    if layout.is_multi_root:
        if not target_project_key:
            if layout.default_project:
                target_project_key = layout.default_project
            else:
                available = [k for k in layout.all_project_keys() if k is not None]
                print(f"Error: Multiple projects configured. Use --project <name> (available: {', '.join(available)})")
                return 1
        elif target_project_key not in layout.roots:
            available = [k for k in layout.all_project_keys() if k is not None]
            print(f"Error: Unknown project '{target_project_key}'. Available: {', '.join(available)}")
            return 1

    # Get target root path
    try:
        target_root = layout.artifact_root(target_project_key)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    # Detect source root - assume .onward/ if it exists
    default_source = root / ".onward"
    if not default_source.exists() or not (default_source / "plans").exists():
        print("Nothing to migrate: .onward/ directory not found or already migrated")
        return 0

    source_root = default_source
    target_root_rel = target_root.relative_to(root) if target_root.is_relative_to(root) else target_root
    source_root_rel = source_root.relative_to(root) if source_root.is_relative_to(root) else source_root

    # Check if source and target are the same
    if source_root.resolve() == target_root.resolve():
        print(f"Nothing to migrate: source and target are the same ({source_root_rel})")
        return 0

    # List of subdirectories and files to migrate
    items_to_migrate = [
        ("plans", True),  # (path, is_directory)
        ("runs", True),
        ("reviews", True),
        ("templates", True),
        ("prompts", True),
        ("hooks", True),
        ("notes", True),
        ("sync", True),
        ("ongoing.json", False),
    ]

    # Check if source has any content to migrate
    has_content = False
    for item_name, is_dir in items_to_migrate:
        item_path = source_root / item_name
        if item_path.exists():
            has_content = True
            break

    if not has_content:
        print(f"Nothing to migrate: {source_root_rel}/ is empty or already migrated")
        return 0

    # Check if target already has content (unless --force)
    if not force:
        target_has_content = False
        for item_name, is_dir in items_to_migrate:
            target_item = target_root / item_name
            if target_item.exists():
                if is_dir and any(target_item.iterdir()):
                    target_has_content = True
                    break
                elif not is_dir:
                    target_has_content = True
                    break

        if target_has_content:
            print(f"Error: Target {target_root_rel}/ already has content. Use --force to overwrite")
            return 1

    # Ensure target directory structure exists
    if not dry_run:
        target_root.mkdir(parents=True, exist_ok=True)
        for subdir in ["plans", "plans/.archive", "templates", "prompts", "hooks", "sync", "runs", "reviews", "notes"]:
            (target_root / subdir).mkdir(parents=True, exist_ok=True)

    # Perform migration
    moved_count = 0
    for item_name, is_dir in items_to_migrate:
        source_item = source_root / item_name
        target_item = target_root / item_name

        if not source_item.exists():
            continue

        if dry_run:
            print(f"Would move: {source_root_rel}/{item_name} → {target_root_rel}/{item_name}")
            moved_count += 1
        else:
            try:
                if is_dir:
                    # For directories, move contents
                    if target_item.exists():
                        # Merge contents if target exists
                        for subitem in source_item.iterdir():
                            target_subitem = target_item / subitem.name
                            if subitem.is_dir():
                                if target_subitem.exists():
                                    shutil.rmtree(target_subitem)
                                shutil.copytree(subitem, target_subitem)
                            else:
                                shutil.copy2(subitem, target_subitem)
                        # Remove source after copying
                        shutil.rmtree(source_item)
                    else:
                        shutil.move(str(source_item), str(target_item))
                else:
                    # For files, just move
                    if target_item.exists():
                        target_item.unlink()
                    shutil.move(str(source_item), str(target_item))

                moved_count += 1
                print(f"Moved: {source_root_rel}/{item_name} → {target_root_rel}/{item_name}")
            except Exception as exc:
                print(f"Warning: Failed to move {item_name}: {exc}")

    if not dry_run and moved_count > 0:
        # Update .gitignore
        _update_gitignore_for_migration(root, str(source_root_rel), str(target_root_rel))
        print(f"Updated .gitignore entries")

        # Try to remove empty source directory
        try:
            if source_root.exists() and not any(source_root.iterdir()):
                source_root.rmdir()
                print(f"Removed empty directory: {source_root_rel}/")
        except Exception:
            pass  # Ignore errors when removing source directory

    if dry_run:
        print(f"\nDry run: {moved_count} items would be migrated")
    else:
        print(f"\nMigration complete: {moved_count} items moved")
        print(f"Run 'onward doctor --root {root}' to verify the migration")

    return 0


def _update_gitignore_for_migration(root: Path, old_root: str, new_root: str) -> None:
    """Update .gitignore entries from old root to new root.

    Args:
        root: Workspace root directory
        old_root: Old artifact root path (relative string)
        new_root: New artifact root path (relative string)
    """
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        # Create .gitignore with new entries
        lines = gitignore_lines(new_root)
        gitignore.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return

    # Read existing .gitignore
    existing_lines = gitignore.read_text(encoding="utf-8").splitlines()
    new_lines = []
    old_entries = gitignore_lines(old_root)
    new_entries = gitignore_lines(new_root)

    # Create mapping from old to new entries
    entry_map = {}
    for old_entry, new_entry in zip(old_entries, new_entries):
        entry_map[old_entry] = new_entry

    # Replace old entries with new ones
    for line in existing_lines:
        if line in entry_map:
            new_lines.append(entry_map[line])
        else:
            new_lines.append(line)

    # Add any new entries that weren't in the old set
    existing_set = set(new_lines)
    for new_entry in new_entries:
        if new_entry not in existing_set:
            new_lines.append(new_entry)

    # Write updated .gitignore
    gitignore.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def cmd_sync_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout)
    code, lines = _cmd_sync_status(root, project)
    for line in lines:
        print(line)
    return code


def cmd_sync_push(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout)
    code, lines = _cmd_sync_push(root, project)
    for line in lines:
        print(line)
    return code


def cmd_sync_pull(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout)
    code, lines = _cmd_sync_pull(root, project)
    for line in lines:
        print(line)
    return code


def cmd_new_plan(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout)

    plan_id = next_id(layout, "PLAN", project)
    now = now_iso()
    slug = slugify(args.title)

    plan_dir = layout.plans_dir(project) / f"{plan_id}-{slug}"
    plan_dir.mkdir(parents=True, exist_ok=False)
    (plan_dir / "chunks").mkdir(parents=True, exist_ok=True)
    (plan_dir / "tasks").mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": plan_id,
        "type": "plan",
        "project": project or "",
        "title": args.title,
        "status": "open",
        "description": args.description or "",
        "priority": args.priority,
        "model": args.model,
        "created_at": now,
        "updated_at": now,
    }

    body = load_artifact_template(root, "plan", layout, project)
    target = plan_dir / "plan.md"
    target.write_text(format_artifact(metadata, body), encoding="utf-8")

    regenerate_indexes(layout)
    target_rel = str(target.relative_to(root))
    print(f"Created {plan_id} at {target_rel}")
    print(
        f"Plan created at {target_rel}. It is currently an empty template. Inspect it for guidance on how to fill it out."
    )
    return 0


def cmd_new_chunk(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    plan_id = args.plan_id

    # Enforce project requirement for layout resolution
    layout_project = require_project_or_default(args, layout)

    # Find the plan using the enforced project
    plan_art = find_by_id(layout, plan_id, layout_project)
    if not plan_art:
        raise ValueError(f"plan not found: {plan_id}")
    if str(plan_art.metadata.get("type", "")) != "plan":
        raise ValueError(f"{plan_id} is not a plan")

    # Determine chunk's project metadata: explicit arg if provided, otherwise inherit from plan
    explicit_project = (args.project or "").strip()
    if explicit_project:
        proj = explicit_project
    else:
        # Inherit from plan when --project was not explicitly provided
        proj = artifact_project(plan_art)

    plan_dir = find_plan_dir(layout, plan_id, proj)
    chunk_id = next_id(layout, "CHUNK", proj)
    now = now_iso()
    slug = slugify(args.title)

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

    body = load_artifact_template(root, "chunk", layout, proj)
    target = plan_dir / "chunks" / f"{chunk_id}-{slug}.md"
    target.write_text(format_artifact(metadata, body), encoding="utf-8")

    regenerate_indexes(layout)
    print(f"Created {chunk_id} at {target.relative_to(root)}")
    return 0


_BATCH_DEP_INDEX = re.compile(r"^\$(\d+)$")


def cmd_new_task_batch(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)

    # Enforce project requirement for layout resolution
    layout_project = require_project_or_default(args, layout)

    # Find the chunk using the enforced project
    chunk = find_by_id(layout, args.chunk_id, layout_project)
    if not chunk:
        raise ValueError(f"chunk not found: {args.chunk_id}")
    if str(chunk.metadata.get("type", "")) != "chunk":
        raise ValueError(f"{args.chunk_id} is not a chunk")

    # Determine base project for batch: explicit arg if provided, otherwise inherit from chunk
    explicit_project = (args.project or "").strip()
    if explicit_project:
        base_project = explicit_project
    else:
        base_project = artifact_project(chunk)

    plan_id = str(chunk.metadata["plan"])
    chunk_id = str(chunk.metadata["id"])
    plan_dir = find_plan_dir(layout, plan_id, base_project)

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

    task_ids = next_ids(layout, "TASK", len(raw), base_project)
    body_template = load_artifact_template(root, "task", layout, base_project)
    writes: list[tuple[str, Path, str]] = []

    for i, entry in enumerate(raw):
        assert isinstance(entry, dict)
        title = clean_string(entry.get("title", ""))
        desc = clean_string(entry.get("description", ""))
        model = clean_string(entry.get("model", "")) or "sonnet-4-6"
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
    regenerate_indexes(layout)
    for tid, path, _ in writes:
        print(f"Created {tid} at {path.relative_to(root)}")
    return 0


def cmd_new_task(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if getattr(args, "batch", None):
        return cmd_new_task_batch(args)

    if not args.title:
        raise ValueError("task title is required unless --batch is used")

    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)

    # Enforce project requirement for layout resolution
    layout_project = require_project_or_default(args, layout)

    # Find the chunk using the enforced project
    chunk = find_by_id(layout, args.chunk_id, layout_project)
    if not chunk:
        raise ValueError(f"chunk not found: {args.chunk_id}")
    if chunk.metadata.get("type") != "chunk":
        raise ValueError(f"{args.chunk_id} is not a chunk")

    # Determine task's project metadata: explicit arg if provided, otherwise inherit from chunk
    explicit_project = (args.project or "").strip()
    if explicit_project:
        proj = explicit_project
    else:
        # Inherit from chunk when --project was not explicitly provided
        proj = artifact_project(chunk)

    plan_id = str(chunk.metadata["plan"])
    chunk_id = str(chunk.metadata["id"])
    task_id = next_id(layout, "TASK", proj)
    now = now_iso()
    slug = slugify(args.title)

    plan_dir = find_plan_dir(layout, plan_id, proj)

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

    body = load_artifact_template(root, "task", layout, proj)
    target = plan_dir / "tasks" / f"{task_id}-{slug}.md"
    target.write_text(format_artifact(metadata, body), encoding="utf-8")

    regenerate_indexes(layout)
    print(f"Created {task_id} at {target.relative_to(root)}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    artifact_type = args.type
    project_filter = require_project_or_default(args, layout, enforce=False)
    blockers_only = bool(args.blocking)
    human_only = bool(args.human)

    indexed = list_from_index(
        layout,
        type_filter=artifact_type,
        project_filter=project_filter or "",
        blocking=blockers_only,
        human_only=human_only,
    )
    if indexed is not None:
        rows = indexed
    else:
        artifacts = collect_artifacts(layout, project_filter)
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


def _format_duration(started_at: str | None, finished_at: str | None) -> str:
    """Return a human-readable duration string like ``2m13s`` or ``-`` when unavailable."""
    if not started_at or not finished_at:
        return "-"
    try:
        from datetime import datetime, timezone
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        s = datetime.strptime(started_at, fmt).replace(tzinfo=timezone.utc)
        f = datetime.strptime(finished_at, fmt).replace(tzinfo=timezone.utc)
        secs = int((f - s).total_seconds())
        if secs < 0:
            return "-"
        minutes, seconds = divmod(secs, 60)
        return f"{minutes}m{seconds:02d}s"
    except Exception:  # noqa: BLE001
        return "-"


def _format_tokens(token_usage: dict[str, Any] | None) -> str:
    """Return ``1.2k/4.5k tokens`` or ``-`` when unavailable."""
    if not isinstance(token_usage, dict):
        return "-"
    inp = token_usage.get("input_tokens")
    out = token_usage.get("output_tokens")
    if inp is None and out is None:
        return "-"
    inp_s = f"{inp / 1000:.1f}k" if inp is not None else "?"
    out_s = f"{out / 1000:.1f}k" if out is not None else "?"
    return f"{inp_s}/{out_s} tokens"


def _print_runs_table(layout: WorkspaceLayout, artifact_id: str, project: str | None = None) -> None:
    """Print a tabular run history for ``artifact_id``."""
    tty = sys.stdout.isatty()
    runs = collect_runs_for_target(layout, artifact_id, limit=20, project=project)
    if not runs:
        print(f"Runs for {artifact_id}: No runs yet")
        return
    runs_sorted = list(reversed(runs))
    print(f"Runs for {artifact_id} ({len(runs_sorted)} run{'s' if len(runs_sorted) != 1 else ''}):")
    for i, r in enumerate(runs_sorted, start=1):
        st = str(r.get("status", ""))
        st_disp = colorize(st, status_color(st), tty)
        ts = str(r.get("started_at") or "-")
        dur = _format_duration(str(r.get("started_at") or ""), str(r.get("finished_at") or ""))
        model = str(r.get("model") or "-")
        tok = _format_tokens(r.get("token_usage"))
        fc = r.get("files_changed")
        file_count = len(fc) if isinstance(fc, list) else 0
        print(f"  #{i}  {ts}  {st_disp}  {dur}  {model}  {tok}  {file_count} files")


def _print_task_show_extras(root: Path, artifact: Artifact, layout: WorkspaceLayout, project: str | None) -> None:
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

    runs = collect_runs_for_target(layout, artifact_id, limit=10, project=project)
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

    artifacts = collect_artifacts(layout, project)
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
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout, enforce=False)
    artifact = find_by_id(layout, args.id, project)
    if not artifact:
        print(f"Artifact not found: {args.id}")
        return 1

    # If project filter was explicitly provided, validate artifact matches
    explicit_project_filter = (getattr(args, "project", "") or "").strip()
    if explicit_project_filter:
        artifacts = collect_artifacts(layout, None)  # Search all for resolution
        by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
        if resolve_project(artifact, by_id) != explicit_project_filter:
            print(f"Artifact not in project {explicit_project_filter!r} (resolved)")
            return 1

    show_runs = getattr(args, "runs", False)
    if show_runs and str(artifact.metadata.get("type", "")) == "task":
        task_id = str(artifact.metadata.get("id", ""))
        _print_runs_table(layout, task_id, project)
        return 0

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
        task_id = str(artifact.metadata.get("id", ""))
        active_claimed = claimed_task_ids(layout, project)
        if task_id in active_claimed:
            ongoing = load_ongoing(layout, project)
            for entry in ongoing.get("active_runs", []):
                if task_id in (entry.get("claimed_children") or []):
                    claim_id = str(entry.get("id", ""))
                    claim_target = str(entry.get("target", ""))
                    print(f"\nClaimed by {claim_id} (running {claim_target})")
                    break
        _print_task_show_extras(root, artifact, layout, project)
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    search_project = require_project_or_default(args, layout, enforce=False)
    artifact = must_find_by_id(layout, args.id, search_project)
    artifact_id = str(artifact.metadata.get("id", ""))
    project = artifact_project(artifact)

    message = getattr(args, "message", None)
    if message:
        path = append_note(layout, artifact, message, project)
        print(f"Note added to {artifact_id} at {path.relative_to(root)}")
        return 0

    notes = read_notes(layout, artifact_id, project)
    if not notes.strip():
        print(f"No notes for {artifact_id}.")
        return 0

    print(f"Notes for {artifact_id}:\n")
    print(notes.rstrip())
    return 0


def _cmd_set_status(args: argparse.Namespace, action: str) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout, enforce=False)
    artifact = must_find_by_id(layout, args.id, project)

    current = str(artifact.metadata.get("status", ""))
    artifact.metadata["status"] = transition_status(current, action)
    artifact.metadata["updated_at"] = now_iso()
    write_artifact(artifact)

    regenerate_indexes(layout)
    artifact_id = str(artifact.metadata.get("id", ""))
    print(f"{artifact_id} status: {current} -> {artifact.metadata.get('status')}")

    if action == "complete":
        _, warnings = finalize_chunks_all_tasks_terminal(layout, project)
        for w in warnings:
            print(w)

    if action in {"complete", "cancel"}:
        notes = read_notes(layout, artifact_id, project)
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
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout, enforce=False)
    artifact = must_find_by_id(layout, args.id, project)
    if str(artifact.metadata.get("type", "")) != "task":
        raise ValueError("onward retry only applies to tasks (TASK-###)")
    current = str(artifact.metadata.get("status", ""))
    artifact.metadata["status"] = transition_status(current, "retry")
    artifact.metadata["run_count"] = 0
    artifact.metadata["updated_at"] = now_iso()
    write_artifact(artifact)
    regenerate_indexes(layout)
    artifact_id = str(artifact.metadata.get("id", ""))
    print(f"{artifact_id} status: {current} -> {artifact.metadata.get('status')}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout, enforce=False)

    artifact = must_find_by_id(layout, args.plan_id, project)
    if artifact.metadata.get("type") != "plan":
        raise ValueError(f"{args.plan_id} is not a plan")

    plan_dir = find_plan_dir(layout, str(artifact.metadata["id"]), project)
    project = artifact_project(artifact)
    archive_dir = layout.archive_dir(project)
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / plan_dir.name

    if target.exists():
        raise ValueError(f"archive target already exists: {target.relative_to(root)}")

    plan_dir.rename(target)
    regenerate_indexes(layout)
    print(f"Archived {args.plan_id} -> {target.relative_to(root)}")
    return 0


def cmd_review_plan(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    require_workspace(root)
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout, enforce=False)

    plan = must_find_by_id(layout, args.plan_id, project)
    plan_type = str(plan.metadata.get("type", ""))
    if plan_type != "plan":
        raise ValueError(f"{args.plan_id} is not a plan (type={plan_type})")

    project = artifact_project(plan)

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

    prompt_path = layout.prompts_dir(project) / "review-plan.md"
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
                layout,
                plan,
                tri.model,
                slot.label,
                prompt,
                executor_command=tri.executor,
                executor_args=list(tri.executor_args),
                emit_errors=is_last,
                project=project,
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


def _status_by_id(layout: WorkspaceLayout, project: str | None = None) -> dict[str, str]:
    return {
        str(a.metadata.get("id", "")): str(a.metadata.get("status", ""))
        for a in collect_artifacts(layout, project)
        if str(a.metadata.get("id", ""))
    }


def _chunk_depends_satisfied(chunk: Artifact, status_by_id: dict[str, str]) -> bool:
    for dep in as_str_list(chunk.metadata.get("depends_on")):
        if status_by_id.get(dep) != "completed":
            return False
    return True


def _plan_chunks(layout: WorkspaceLayout, plan_id: str, project: str | None = None) -> list[Artifact]:
    chunks = [
        a
        for a in collect_artifacts(layout, project)
        if str(a.metadata.get("type", "")) == "chunk"
        and str(a.metadata.get("plan", "")) == plan_id
    ]
    return sorted(chunks, key=lambda a: str(a.metadata.get("id", "")))


def _work_chunk(layout: WorkspaceLayout, chunk: Artifact, config: dict[str, Any], project: str | None = None) -> int:
    return work_chunk(layout, chunk, config, project)


def _work_plan(layout: WorkspaceLayout, plan: Artifact, config: dict[str, Any], project: str | None = None) -> int:
    root = layout.workspace_root
    plan_id = str(plan.metadata.get("id", ""))
    st = str(plan.metadata.get("status", ""))
    if st == "completed":
        print(f"Plan {plan_id} already completed")
        return 0

    chunks = _plan_chunks(layout, plan_id, project)
    if not chunks:
        print(f"Plan {plan_id} has no chunks")
        return 0

    if st in {"open", "in_progress"}:
        update_artifact_status(layout, plan, "in_progress", project)

    for c in chunks:
        cid = str(c.metadata.get("id", ""))
        if str(c.metadata.get("status", "")) == "completed":
            bad = chunk_has_nonterminal_tasks(layout, cid, project)
            if bad:
                print(
                    f"Chunk {cid} was marked completed but has non-terminal tasks: "
                    f"{', '.join(bad)} — reopening chunk"
                )
                update_artifact_status(layout, must_find_by_id(layout, cid, project), "in_progress", project)

    chunks = _plan_chunks(layout, plan_id, project)
    pending = [
        str(c.metadata.get("id", ""))
        for c in chunks
        if str(c.metadata.get("status", "")) not in {"completed", "canceled"}
    ]
    if not pending:
        refreshed_plan = must_find_by_id(layout, plan_id, project)
        update_artifact_status(layout, refreshed_plan, "completed", project)
        _, warnings = finalize_chunks_all_tasks_terminal(layout, project)
        for w in warnings:
            print(w)
        n_tasks = sum(
            1
            for a in collect_artifacts(layout, project)
            if str(a.metadata.get("type", "")) == "task"
            and str(a.metadata.get("plan", "")) == plan_id
            and str(a.metadata.get("status", "")) == "completed"
        )
        print(f"Plan {plan_id} completed ({len(chunks)} chunks, {n_tasks} tasks)")
        return 0

    while pending:
        status_by_id = _status_by_id(layout, project)
        ready = [
            cid
            for cid in pending
            if _chunk_depends_satisfied(must_find_by_id(layout, cid, project), status_by_id)
        ]
        if not ready:
            print(
                f"Plan {plan_id}: no chunk is ready to run (check chunk depends_on / ordering)"
            )
            return 1
        cid = min(ready)
        chunk_art = must_find_by_id(layout, cid, project)
        chunk_claimed = [
            str(a.metadata.get("id", ""))
            for a in collect_artifacts(layout, project)
            if str(a.metadata.get("type", "")) == "task"
            and str(a.metadata.get("chunk", "")) == cid
            and str(a.metadata.get("status", "")) in {"open", "in_progress"}
        ]
        plan_claim_id = f"CLAIM-{run_timestamp()}-{cid}"
        register_claim(layout, plan_claim_id, cid, "plan", chunk_claimed, os.getpid(), project)
        try:
            code = _work_chunk(layout, chunk_art, config, project)
        finally:
            release_claim(layout, plan_claim_id, project)
        if code != 0:
            print(f"Stopping plan work for {plan_id} after chunk {cid} failure")
            return 1
        pending.remove(cid)

    refreshed_plan = must_find_by_id(layout, plan_id, project)
    update_artifact_status(layout, refreshed_plan, "completed", project)
    _, warnings = finalize_chunks_all_tasks_terminal(layout, project)
    for w in warnings:
        print(w)
    n_tasks = sum(
        1
        for a in collect_artifacts(layout, project)
        if str(a.metadata.get("type", "")) == "task"
        and str(a.metadata.get("plan", "")) == plan_id
        and str(a.metadata.get("status", "")) == "completed"
    )
    print(f"Plan {plan_id} completed ({len(chunks)} chunks, {n_tasks} tasks)")
    return 0


def cmd_work(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    search_project = require_project_or_default(args, layout, enforce=False)
    artifact = must_find_by_id(layout, args.id, search_project)
    artifact_type = str(artifact.metadata.get("type", ""))
    project = artifact_project(artifact)

    if artifact_type == "task":
        ok, run_id = work_task(layout, artifact, project)
        if run_id:
            print(f"Run {run_id}: {'completed' if ok else 'failed'}")
        else:
            print(f"{args.id} already completed")
        if ok and run_id and not getattr(args, "no_follow_ups", False):
            rec = collect_runs_for_target(layout, args.id, limit=1, project=project)
            run_rec = rec[0] if rec else {}
            tr = run_rec.get("task_result") or {}
            fus = tr.get("follow_ups") or []
            if isinstance(fus, list) and fus:
                parent = must_find_by_id(layout, args.id, search_project)
                created, fu_warnings = create_follow_up_tasks(layout, parent, fus, project)
                for w in fu_warnings:
                    print(f"Warning: {w}")
                for cid in created:
                    print(f"Created follow-up task {cid}")
        if ok:
            _, warnings = finalize_chunks_all_tasks_terminal(layout, project)
            for w in warnings:
                print(w)
        return 0 if ok else 1
    if artifact_type == "plan":
        return _work_plan(layout, artifact, config, project)
    if artifact_type != "chunk":
        raise ValueError(f"{args.id} is not a task, chunk, or plan")
    return _work_chunk(layout, artifact, config, project)


def cmd_split(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    search_project = require_project_or_default(args, layout, enforce=False)

    artifact = must_find_by_id(layout, args.id, search_project)
    artifact_type = str(artifact.metadata.get("type", ""))
    if artifact_type not in {"plan", "chunk"}:
        raise ValueError(f"{args.id} is not splittable (expected PLAN-* or CHUNK-*)")

    project = artifact_project(artifact)

    default_model = model_setting(config, "default", "opus-latest")
    split_model = clean_string(args.model) or model_setting(config, "split_default", "") or default_model
    task_default_model = model_setting(config, "task_default", "sonnet-4-6")

    prompt_name = "split-plan.md" if artifact_type == "plan" else "split-chunk.md"
    raw = run_split_model(
        root,
        artifact,
        prompt_name,
        split_model,
        task_default_model,
        heuristic=bool(getattr(args, "heuristic", False)),
        config=config,
        layout=layout,
        project=project,
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
        prompt_path = layout.prompts_dir(project) / prompt_name
        print(f"Split dry-run ({split_kind}) for {args.id} using model={split_model}")
        print(f"Prompt: {prompt_path.relative_to(root)}")
        for artifact_id, path, _content in writes:
            print(f"{child_type}: create {artifact_id}\t{path.relative_to(root)}")
        return 0

    for _artifact_id, path, content in writes:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    regenerate_indexes(layout)

    for artifact_id, path, _content in writes:
        print(f"Created {artifact_id} at {path.relative_to(root)}")
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout, enforce=False)
    artifacts = collect_artifacts(layout, project)
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
        ongoing = load_ongoing(layout, project)
        active = ongoing.get("active_runs", [])
        if not isinstance(active, list) or not active:
            print("No in-progress artifacts")
            return 0
    else:
        for row in sorted(rows):
            print(row)

    ongoing = load_ongoing(layout, project)
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
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout, enforce=False)
    artifacts = collect_artifacts(layout, project)
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

    for rec in collect_run_records(layout, project):
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
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout, enforce=False)
    _, warnings = finalize_chunks_all_tasks_terminal(layout, project)
    for w in warnings:
        print(w)
    artifacts = artifacts_from_index_or_collect(layout, project)
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
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
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout, enforce=False)
    _, warnings = finalize_chunks_all_tasks_terminal(layout, project)
    for w in warnings:
        print(w)
    artifacts = artifacts_from_index_or_collect(layout, project)
    active_claimed = claimed_task_ids(layout, project)
    chosen = select_next_artifact(
        artifacts,
        project=project,
        claimed_ids=active_claimed,
    )
    if chosen:
        # In multi-root mode with project=None, include project name in output
        by_id = {str(a.metadata.get("id", "")): a for a in artifacts if a.metadata.get("id")}
        artifact_project = resolve_project(chosen, by_id)
        if layout.is_multi_root and project is None and artifact_project:
            print(
                f"[{artifact_project}] {chosen.metadata.get('id')}\t{chosen.metadata.get('type')}\t{chosen.metadata.get('status')}\t{chosen.metadata.get('title')}\t{chosen.file_path.relative_to(root)}"
            )
        else:
            print(
                f"{chosen.metadata.get('id')}\t{chosen.metadata.get('type')}\t{chosen.metadata.get('status')}\t{chosen.metadata.get('title')}\t{chosen.file_path.relative_to(root)}"
            )
        return 0

    print("No next artifact found")
    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    project = require_project_or_default(args, layout, enforce=False)
    artifacts = artifacts_from_index_or_collect(layout, project)
    lines = render_active_work_tree_lines(artifacts, layout, project=project, color_enabled=not args.no_color)
    if not lines:
        print("No active work tree (no open plans)")
        return 0
    for line in lines:
        print(line)
    return 0


def format_report_markdown(
    layout: WorkspaceLayout,
    project: str | None,
    artifacts: list[Artifact],
    blockers: set[str],
    by_id: dict[str, Artifact],
    active_claimed: set[str],
    limit: int,
    verbose: bool,
) -> str:
    """Format report data as clean markdown (no ANSI codes)."""
    lines: list[str] = []

    # Header
    lines.append("# Onward Report")
    lines.append("")
    if project:
        lines.append(f"**Project:** {project}")
    lines.append(f"**Generated:** {now_iso()}")
    lines.append("")

    # Effort Remaining
    lines.append("## Effort Remaining")
    lines.append("")
    eff_counts = summarize_effort_remaining(artifacts)
    headers = ["xs", "s", "m", "l", "xl", "unestimated"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    lines.append("| " + " | ".join(str(eff_counts[k]) for k in headers) + " |")
    lines.append("")

    # In Progress
    lines.append("## In Progress")
    lines.append("")
    in_progress = report_rows(artifacts, layout, status="in_progress", project=project, claimed_ids=active_claimed)
    if in_progress:
        lines.append("| ID | Type | Status | Title |")
        lines.append("|---|---|---|---|")
        for row in in_progress:
            parts = row.split("\t")[:4]
            lines.append("| " + " | ".join(parts) + " |")
    else:
        lines.append("*None*")
    lines.append("")

    # Upcoming
    lines.append("## Upcoming")
    lines.append("")
    upcoming = report_rows(artifacts, layout, status="open", project=project, claimed_ids=active_claimed)
    if upcoming:
        lines.append("| ID | Type | Status | Title |")
        lines.append("|---|---|---|---|")
        for row in upcoming:
            parts = row.split("\t")[:4]
            lines.append("| " + " | ".join(parts) + " |")
    else:
        lines.append("*None*")
    lines.append("")

    # Claimed (if any)
    if active_claimed:
        lines.append("## Claimed")
        lines.append("")
        c_rows = claimed_rows(artifacts, layout, active_claimed, project=project)
        if c_rows:
            lines.append("| ID | Type | Status | Title |")
            lines.append("|---|---|---|---|")
            for row in c_rows:
                parts = row.split("\t")[:4]
                lines.append("| " + " | ".join(parts) + " |")
        else:
            lines.append("*None*")
        lines.append("")

    # Next
    lines.append("## Next")
    lines.append("")
    nxt = select_next_artifact(artifacts, project=project, claimed_ids=active_claimed)
    if nxt:
        status = str(nxt.metadata.get("status", ""))
        artifact_id = str(nxt.metadata.get("id", ""))
        artifact_type = str(nxt.metadata.get("type", ""))
        title = str(nxt.metadata.get("title", ""))
        lines.append(f"- **{artifact_id}** ({artifact_type}, {status}): {title}")
    else:
        lines.append("*None*")
    lines.append("")

    # Blocking Human Tasks
    lines.append("## Blocking Human Tasks")
    lines.append("")
    human_blockers: list[tuple[str, str, str, str]] = []
    for blocker_id in sorted(blockers):
        artifact = by_id.get(blocker_id)
        if not artifact:
            continue
        if project and resolve_project(artifact, by_id) != project:
            continue
        if not is_human_task(artifact):
            continue
        human_blockers.append((
            blocker_id,
            "task",
            str(artifact.metadata.get("status", "")),
            str(artifact.metadata.get("title", "")),
        ))
    if human_blockers:
        lines.append("| ID | Type | Status | Title |")
        lines.append("|---|---|---|---|")
        for parts in human_blockers:
            lines.append("| " + " | ".join(parts) + " |")
    else:
        lines.append("*None*")
    lines.append("")

    # Recent Completed
    lines.append("## Recent Completed")
    lines.append("")
    completed = [
        a
        for a in artifacts
        if str(a.metadata.get("status", "")) == "completed"
        and (not project or resolve_project(a, by_id) == project)
    ]
    completed.sort(key=lambda a: str(a.metadata.get("updated_at", "")), reverse=True)
    if completed:
        slice_ = completed[:limit]
        lines.append("| Completed | Breadcrumb | Title |")
        lines.append("|---|---|---|")
        for artifact in slice_:
            artifact_id = str(artifact.metadata.get("id", ""))
            artifact_type = str(artifact.metadata.get("type", ""))
            updated = str(artifact.metadata.get("updated_at", ""))
            title = str(artifact.metadata.get("title", ""))
            if artifact_type == "task":
                chunk_id = str(artifact.metadata.get("chunk", "") or "")
                plan_id = str(artifact.metadata.get("plan", "") or "")
                parts = [p for p in [plan_id, chunk_id, artifact_id] if p]
            elif artifact_type == "chunk":
                plan_id = str(artifact.metadata.get("plan", "") or "")
                parts = [p for p in [plan_id, artifact_id] if p]
            else:
                parts = [artifact_id]
            breadcrumb = " > ".join(parts)
            lines.append(f"| {updated} | {breadcrumb} | {title} |")
    else:
        lines.append("*None*")
    lines.append("")

    # Active Work Tree
    lines.append("## Active Work Tree")
    lines.append("")
    tree_lines = render_active_work_tree_lines(artifacts, layout, project=project, color_enabled=False)
    if not tree_lines:
        lines.append("*None*")
    else:
        lines.append("```")
        lines.extend(tree_lines)
        lines.append("```")
    lines.append("")

    # Run Stats (if verbose)
    if verbose:
        lines.append("## Run Stats")
        lines.append("")
        task_ids = [
            str(a.metadata.get("id", ""))
            for a in artifacts
            if str(a.metadata.get("type", "")) == "task"
            and str(a.metadata.get("id", ""))
            and (not project or resolve_project(a, by_id) == project)
        ]
        all_runs: list[dict[str, Any]] = []
        for tid in task_ids:
            all_runs.extend(collect_runs_for_target(root, tid, limit=100))
        total = len(all_runs)
        if total == 0:
            lines.append("| Metric | Value |")
            lines.append("|---|---|")
            lines.append("| Total runs | 0 |")
            lines.append("| Pass rate | n/a |")
            lines.append("| Total tokens | n/a |")
        else:
            completed_count = sum(1 for r in all_runs if str(r.get("status", "")) == "completed")
            failed_count = sum(1 for r in all_runs if str(r.get("status", "")) == "failed")
            pass_rate = completed_count / total * 100
            total_input = 0
            total_output = 0
            has_tokens = False
            for r in all_runs:
                tu = r.get("token_usage")
                if isinstance(tu, dict):
                    inp = tu.get("input_tokens")
                    out = tu.get("output_tokens")
                    if inp is not None:
                        total_input += int(inp)
                        has_tokens = True
                    if out is not None:
                        total_output += int(out)
                        has_tokens = True
            lines.append("| Metric | Value |")
            lines.append("|---|---|")
            lines.append(f"| Total runs | {total} ({completed_count} completed, {failed_count} failed) |")
            if has_tokens:
                inp_s = f"{total_input / 1000:.1f}k"
                out_s = f"{total_output / 1000:.1f}k"
                lines.append(f"| Total tokens | {inp_s} input / {out_s} output |")
            else:
                lines.append("| Total tokens | n/a |")
            lines.append(f"| Pass rate | {pass_rate:.1f}% |")
        lines.append("")

    return "\n".join(lines)


def _cmd_report_multi_project(
    args: argparse.Namespace,
    root: Path,
    config: dict[str, Any],
    layout: WorkspaceLayout,
    color_enabled: bool,
) -> int:
    """Generate combined multi-project report when in multi-root mode with project=None."""
    print(colorize("== Onward Multi-Project Report ==", "bold", color_enabled))
    print()

    # Load all artifacts from all roots
    artifacts = artifacts_from_index_or_collect(layout, None)
    blockers = blocking_ids(artifacts)
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts}

    # Get all project keys
    project_keys = [k for k in layout.all_project_keys() if k is not None]
    if not project_keys:
        print("No projects configured.")
        return 0

    # Overall summary
    print(colorize("[Overall Summary]", "cyan", color_enabled))
    total_effort = summarize_effort_remaining(artifacts)
    print(
        "  "
        + "  ".join(
            f"{k}: {total_effort[k]}"
            for k in ("xs", "s", "m", "l", "xl", "unestimated")
        )
    )
    print()

    # Per-project reports
    for proj_key in sorted(project_keys):
        print(colorize(f"== Project: {proj_key} ==", "bold", color_enabled))
        print()

        # Filter artifacts for this project
        proj_artifacts = [a for a in artifacts if resolve_project(a, by_id) == proj_key]
        proj_claimed = claimed_task_ids(layout, proj_key)

        # Effort remaining
        print(colorize("[Effort remaining]", "cyan", color_enabled))
        eff_counts = summarize_effort_remaining(proj_artifacts)
        print(
            "  "
            + "  ".join(
                f"{k}: {eff_counts[k]}"
                for k in ("xs", "s", "m", "l", "xl", "unestimated")
            )
        )
        print()

        # In Progress
        print(colorize("[In Progress]", "cyan", color_enabled))
        in_progress = report_rows(proj_artifacts, layout, status="in_progress", project=proj_key, claimed_ids=proj_claimed)
        if in_progress:
            for row in in_progress:
                parts = row.split("\t")
                parts[2] = colorize(parts[2], status_color(parts[2]), color_enabled)
                print("\t".join(parts))
        else:
            print("none")
        print()

        # Upcoming
        print(colorize("[Upcoming (top 5)]", "cyan", color_enabled))
        upcoming = report_rows(proj_artifacts, layout, status="open", project=proj_key, claimed_ids=proj_claimed)
        if upcoming:
            for row in upcoming[:5]:  # Show top 5 for combined view
                parts = row.split("\t")
                parts[2] = colorize(parts[2], status_color(parts[2]), color_enabled)
                print("\t".join(parts))
            if len(upcoming) > 5:
                print(f"  ... and {len(upcoming) - 5} more")
        else:
            print("none")
        print()

        # Next
        print(colorize("[Next]", "cyan", color_enabled))
        nxt = select_next_artifact(proj_artifacts, project=proj_key, claimed_ids=proj_claimed)
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

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_workspace_config(root)
    layout = WorkspaceLayout.from_config(root, config)
    color_enabled = not args.no_color
    project = require_project_or_default(args, layout, enforce=False)

    # Multi-root mode with project=None: show combined multi-project report
    if layout.is_multi_root and project is None:
        return _cmd_report_multi_project(args, root, config, layout, color_enabled)

    _, warnings = finalize_chunks_all_tasks_terminal(layout, project)
    for w in warnings:
        print(w)
    artifacts = artifacts_from_index_or_collect(layout, project)
    blockers = blocking_ids(artifacts)
    by_id = {str(a.metadata.get("id", "")): a for a in artifacts}
    active_claimed = claimed_task_ids(layout, project)

    # If --md flag is set, output markdown and return early
    if getattr(args, "md", False):
        md = format_report_markdown(
            layout=layout,
            project=project,
            artifacts=artifacts,
            blockers=blockers,
            by_id=by_id,
            active_claimed=active_claimed,
            limit=args.limit,
            verbose=getattr(args, "verbose", False),
        )
        print(md)
        return 0

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
    in_progress = report_rows(artifacts, layout, status="in_progress", project=project, claimed_ids=active_claimed)
    if in_progress:
        for row in in_progress:
            parts = row.split("\t")
            parts[2] = colorize(parts[2], status_color(parts[2]), color_enabled)
            print("\t".join(parts))
    else:
        print("none")
    print()

    print(colorize("[Upcoming]", "cyan", color_enabled))
    upcoming = report_rows(artifacts, layout, status="open", project=project, claimed_ids=active_claimed)
    if upcoming:
        for row in upcoming:
            parts = row.split("\t")
            parts[2] = colorize(parts[2], status_color(parts[2]), color_enabled)
            print("\t".join(parts))
    else:
        print("none")
    print()

    if active_claimed:
        print(colorize("[Claimed]", "cyan", color_enabled))
        c_rows = claimed_rows(artifacts, layout, active_claimed, project=project)
        if c_rows:
            for row in c_rows:
                parts = row.split("\t")
                parts[2] = colorize(parts[2], status_color(parts[2]), color_enabled)
                print("\t".join(parts))
        else:
            print("none")
        print()

    print(colorize("[Next]", "cyan", color_enabled))
    nxt = select_next_artifact(artifacts, project=project, claimed_ids=active_claimed)
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
        slice_ = completed[: args.limit]
        rows = []
        for artifact in slice_:
            artifact_id = str(artifact.metadata.get("id", ""))
            artifact_type = str(artifact.metadata.get("type", ""))
            updated = str(artifact.metadata.get("updated_at", ""))
            title = str(artifact.metadata.get("title", ""))
            if artifact_type == "task":
                chunk_id = str(artifact.metadata.get("chunk", "") or "")
                plan_id = str(artifact.metadata.get("plan", "") or "")
                parts = [p for p in [plan_id, chunk_id, artifact_id] if p]
            elif artifact_type == "chunk":
                plan_id = str(artifact.metadata.get("plan", "") or "")
                parts = [p for p in [plan_id, artifact_id] if p]
            else:
                parts = [artifact_id]
            rows.append((updated, " > ".join(parts), title))
        col_width = max(len(breadcrumb) for _, breadcrumb, _ in rows)
        for updated, breadcrumb, title in rows:
            print(f"{updated}\t{breadcrumb:<{col_width}}\t{title}")
    else:
        print("none")
    print()

    print(colorize("[Active work tree]", "cyan", color_enabled))
    tree_lines = render_active_work_tree_lines(artifacts, root, project=project, color_enabled=color_enabled)
    if not tree_lines:
        print("none")
    else:
        for line in tree_lines:
            print(line)

    if getattr(args, "verbose", False):
        print()
        print(colorize("[Run stats]", "cyan", color_enabled))
        task_ids = [
            str(a.metadata.get("id", ""))
            for a in artifacts
            if str(a.metadata.get("type", "")) == "task"
            and str(a.metadata.get("id", ""))
            and (not project or resolve_project(a, by_id) == project)
        ]
        all_runs: list[dict[str, Any]] = []
        for tid in task_ids:
            all_runs.extend(collect_runs_for_target(root, tid, limit=100))
        total = len(all_runs)
        if total == 0:
            print("  Total runs: 0")
            print("  Pass rate: n/a")
            print("  Total tokens: n/a")
        else:
            completed_count = sum(1 for r in all_runs if str(r.get("status", "")) == "completed")
            failed_count = sum(1 for r in all_runs if str(r.get("status", "")) == "failed")
            pass_rate = completed_count / total * 100
            total_input = 0
            total_output = 0
            has_tokens = False
            for r in all_runs:
                tu = r.get("token_usage")
                if isinstance(tu, dict):
                    inp = tu.get("input_tokens")
                    out = tu.get("output_tokens")
                    if inp is not None:
                        total_input += int(inp)
                        has_tokens = True
                    if out is not None:
                        total_output += int(out)
                        has_tokens = True
            print(f"  Total runs: {total} ({completed_count} completed, {failed_count} failed)")
            if has_tokens:
                inp_s = f"{total_input / 1000:.1f}k"
                out_s = f"{total_output / 1000:.1f}k"
                print(f"  Total tokens: {inp_s} input / {out_s} output")
            else:
                print("  Total tokens: n/a")
            print(f"  Pass rate: {pass_rate:.1f}%")

    return 0

