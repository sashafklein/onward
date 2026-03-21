from __future__ import annotations

import argparse
import sys
from pathlib import Path

from onward.cli_commands import (
    cmd_archive,
    cmd_cancel,
    cmd_complete,
    cmd_doctor,
    cmd_init,
    cmd_list,
    cmd_migrate,
    cmd_new_chunk,
    cmd_new_plan,
    cmd_new_task,
    cmd_next,
    cmd_note,
    cmd_progress,
    cmd_ready,
    cmd_recent,
    cmd_report,
    cmd_retry,
    cmd_review_plan,
    cmd_show,
    cmd_split,
    cmd_sync_pull,
    cmd_sync_push,
    cmd_sync_status,
    cmd_tree,
    cmd_work,
)
from onward.scaffold import require_workspace


# ---------------------------------------------------------------------------
# Parser & entry point
# ---------------------------------------------------------------------------

# Shown on `onward tree` / `onward report --help`; matches render_active_work_tree_lines()
# in artifacts.py (markers from is_human_task).
TASK_MARKER_LEGEND_EPILOG = """
Task markers (each task line in report’s [Active work tree] and in `onward tree`):
  (A)  Agent task — frontmatter human: false (default). Eligible for `onward next` when
       dependencies are satisfied.
  (H)  Human task — human: true; not suggested by `onward next`.
`onward report` also prints [Blocking Human Tasks]: human tasks whose IDs appear in
another open/in-progress artifact’s depends_on list (legacy blocked_by is treated the same).
"""


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

    migrate_parser = subparsers.add_parser("migrate", help="Move artifacts from old root to new configured root")
    migrate_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    migrate_parser.add_argument("--dry-run", action="store_true", help="Print planned moves without executing them")
    migrate_parser.add_argument("--force", action="store_true", help="Overwrite target if it already has content")
    migrate_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    migrate_parser.set_defaults(func=cmd_migrate)

    sync_parser = subparsers.add_parser("sync", help="Sync .onward/plans with a branch or remote repo")
    sync_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    sync_sub = sync_parser.add_subparsers(dest="sync_command", required=True)

    sync_status_parser = sync_sub.add_parser("status", help="Compare local plans with sync target")
    sync_status_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    sync_status_parser.set_defaults(func=cmd_sync_status)

    sync_push_parser = sync_sub.add_parser("push", help="Copy local plans to sync target, commit, and push")
    sync_push_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    sync_push_parser.set_defaults(func=cmd_sync_push)

    sync_pull_parser = sync_sub.add_parser("pull", help="Fast-forward sync target and copy plans locally")
    sync_pull_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    sync_pull_parser.set_defaults(func=cmd_sync_pull)

    new_parser = subparsers.add_parser("new", help="Create new artifacts")
    new_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    new_subparsers = new_parser.add_subparsers(dest="artifact", required=True)

    plan_parser = new_subparsers.add_parser("plan", help="Create a plan")
    plan_parser.add_argument("title", help="Plan title")
    plan_parser.add_argument("--description", default="", help="Plan description")
    plan_parser.add_argument("--priority", default="medium", help="Priority (low|medium|high)")
    plan_parser.add_argument("--model", default="opus-latest", help="Default model")
    plan_parser.add_argument("--project", default=None, help="Optional project key (omit for empty)")
    plan_parser.set_defaults(func=cmd_new_plan)

    chunk_parser = new_subparsers.add_parser("chunk", help="Create a chunk")
    chunk_parser.add_argument("plan_id", help="Owning plan ID (e.g., PLAN-001)")
    chunk_parser.add_argument("title", help="Chunk title")
    chunk_parser.add_argument("--description", default="", help="Chunk description")
    chunk_parser.add_argument("--priority", default="medium", help="Priority (low|medium|high)")
    chunk_parser.add_argument("--model", default="opus-latest", help="Default model")
    chunk_parser.add_argument(
        "--project",
        default=None,
        help="Optional project key (omit to inherit from plan; use --project '' for none)",
    )
    chunk_parser.add_argument(
        "--effort",
        default=None,
        help="T-shirt size: xs|s|m|l|xl (invalid values ignored)",
    )
    chunk_parser.add_argument(
        "--estimated-files",
        type=int,
        default=None,
        help="Rough file touch count for this chunk (informational)",
    )
    chunk_parser.set_defaults(func=cmd_new_chunk)

    task_parser = new_subparsers.add_parser("task", help="Create a task")
    task_parser.add_argument("chunk_id", help="Owning chunk ID (e.g., CHUNK-001)")
    task_parser.add_argument(
        "title",
        nargs="?",
        default=None,
        help="Task title (omit when using --batch)",
    )
    task_parser.add_argument(
        "--batch",
        metavar="FILE",
        default=None,
        help="Create multiple tasks from a JSON array in FILE",
    )
    task_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --batch: validate and print planned tasks without writing files",
    )
    task_parser.add_argument("--description", default="", help="Task description")
    task_parser.add_argument("--model", default="sonnet-4-6", help="Model")
    task_parser.add_argument(
        "--project",
        default=None,
        help="Optional project key (omit to inherit from chunk; use --project '' for none)",
    )
    task_parser.add_argument(
        "--effort",
        default=None,
        help="T-shirt size: xs|s|m|l|xl (invalid values ignored)",
    )
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
    show_parser.add_argument("--project", default="", help="When set, hide artifact if it does not match this project (resolved)")
    show_parser.add_argument("--runs", action="store_true", help="Show run history table for a task")
    show_parser.set_defaults(func=cmd_show)

    note_parser = subparsers.add_parser("note", help="Add or view notes on an artifact")
    note_parser.add_argument("id", help="Artifact ID (PLAN-###, CHUNK-###, TASK-###)")
    note_parser.add_argument("message", nargs="?", default=None, help="Note text (omit to view existing notes)")
    note_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    note_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    note_parser.set_defaults(func=cmd_note)

    complete_parser = subparsers.add_parser("complete", help="Move artifact to completed")
    complete_parser.add_argument("id", help="Artifact ID")
    complete_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    complete_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    complete_parser.set_defaults(func=cmd_complete)

    cancel_parser = subparsers.add_parser("cancel", help="Move artifact to canceled")
    cancel_parser.add_argument("id", help="Artifact ID")
    cancel_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    cancel_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    cancel_parser.set_defaults(func=cmd_cancel)

    retry_parser = subparsers.add_parser(
        "retry",
        help="Reset a failed task to open (clears run_count for another onward work)",
    )
    retry_parser.add_argument("id", help="Task ID (TASK-###)")
    retry_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    retry_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    retry_parser.set_defaults(func=cmd_retry)

    archive_parser = subparsers.add_parser("archive", help="Archive a plan")
    archive_parser.add_argument("plan_id", help="Plan ID (PLAN-###)")
    archive_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    archive_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    archive_parser.set_defaults(func=cmd_archive)

    split_parser = subparsers.add_parser(
        "split",
        help="Split a plan into chunks or a chunk into tasks (AI executor by default; see docs/CAPABILITIES.md)",
    )
    split_parser.add_argument("id", help="Artifact ID (PLAN-### or CHUNK-###)")
    split_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    split_parser.add_argument("--dry-run", action="store_true", help="Print planned artifacts without writing files")
    split_parser.add_argument("--model", default="", help="Override split model")
    split_parser.add_argument(
        "--heuristic",
        action="store_true",
        help="Offline split using markdown heuristics (no executor)",
    )
    split_parser.add_argument(
        "--force",
        action="store_true",
        help="Write artifacts even when split validation reports errors",
    )
    split_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    split_parser.set_defaults(func=cmd_split)

    review_plan_parser = subparsers.add_parser("review-plan", help="Run adversarial review(s) of a plan")
    review_plan_parser.add_argument("plan_id", help="Plan ID (PLAN-###)")
    review_plan_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    review_plan_parser.add_argument(
        "--reviewer",
        action="append",
        dest="reviewer_labels",
        metavar="LABEL",
        help="Run only reviewer slot(s) with this label (exact match; repeat flag for multiple)",
    )
    review_plan_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    review_plan_parser.set_defaults(func=cmd_review_plan)

    work_parser = subparsers.add_parser("work", help="Execute a task or sequentially execute a chunk")
    work_parser.add_argument("id", help="Artifact ID (TASK-### or CHUNK-###)")
    work_parser.add_argument(
        "--no-follow-ups",
        action="store_true",
        help="Do not create tasks from structured follow_ups in the executor result (tasks only)",
    )
    work_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    work_parser.add_argument("--project", default="", help="Project key (required in multi-root mode)")
    work_parser.set_defaults(func=cmd_work)

    progress_parser = subparsers.add_parser("progress", help="Show in-progress artifacts")
    progress_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    progress_parser.add_argument("--project", default="", help="Filter by project key (resolved)")
    progress_parser.set_defaults(func=cmd_progress)

    recent_parser = subparsers.add_parser("recent", help="Show recently completed artifacts")
    recent_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    recent_parser.add_argument("--limit", type=int, default=10, help="Max items to show")
    recent_parser.add_argument("--project", default="", help="Filter by project key (resolved)")
    recent_parser.set_defaults(func=cmd_recent)

    ready_parser = subparsers.add_parser(
        "ready",
        help="List actionable tasks across plans (grouped by plan and chunk)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=TASK_MARKER_LEGEND_EPILOG,
    )
    ready_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    ready_parser.add_argument("--project", default="", help="Filter by project key (resolved)")
    ready_parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    ready_parser.set_defaults(func=cmd_ready)

    next_parser = subparsers.add_parser("next", help="Suggest next open artifact")
    next_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    next_parser.add_argument("--project", default="", help="Filter by project key")
    next_parser.set_defaults(func=cmd_next)

    tree_parser = subparsers.add_parser(
        "tree",
        help="Show open plans with chunks/tasks in open, in_progress, or failed (excludes completed/canceled)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=TASK_MARKER_LEGEND_EPILOG,
    )
    tree_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    tree_parser.add_argument("--project", default="", help="Filter by project key")
    tree_parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    tree_parser.set_defaults(func=cmd_tree)

    report_parser = subparsers.add_parser(
        "report",
        help="Show consolidated colored status report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=TASK_MARKER_LEGEND_EPILOG,
    )
    report_parser.add_argument("--root", default=".", help="Workspace root (default: current directory)")
    report_parser.add_argument("--project", default="", help="Filter by project key")
    report_parser.add_argument("--limit", type=int, default=10, help="Max recent items to show")
    report_parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    report_parser.add_argument("--verbose", action="store_true", help="Show run stats (total runs, tokens, pass rate)")
    report_parser.add_argument("--md", action="store_true", help="Output clean markdown instead of ANSI")
    report_parser.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        # Skip workspace validation for init, doctor, and migrate commands
        # (init creates the workspace, doctor diagnoses workspace issues, migrate moves artifacts)
        if getattr(args, "command", "") not in ("init", "doctor", "migrate"):
            root_value = getattr(args, "root", ".")
            require_workspace(Path(root_value).resolve())
        return args.func(args)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
