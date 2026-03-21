#!/usr/bin/env python3
"""Bootstrap chunk executor — runs tasks through claude CLI serially.

Usage:
    python scripts/run-chunk.py CHUNK-008              # execute all open tasks
    python scripts/run-chunk.py CHUNK-008 --dry-run    # preview task order + prompts
    python scripts/run-chunk.py CHUNK-008 --from TASK-031  # start from a specific task
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from onward.artifacts import (
    collect_artifacts,
    find_by_id,
    must_find_by_id,
    update_artifact_status,
)
from onward.util import clean_string, dump_simple_yaml

MODEL_MAP = {
    "sonnet": "sonnet",
    "opus": "opus",
    "haiku": "haiku",
    "codex": "codex",
}

TASK_SYSTEM_PROMPT = """\
You are completing a task for the Onward project — a git-native planning and execution \
CLI for AI-driven development. The codebase is a Python package (src/onward/) with tests \
in tests/. Entry point: onward.cli:main.

RULES:
1. Read the task carefully — the Scope section is your contract.
2. Read "Files to inspect" FIRST to understand the current code.
3. Make ALL changes described in Scope. Nothing more, nothing less.
4. Run `pytest tests/ -x` and fix any failures you introduce.
5. Do NOT commit or push — the orchestrator handles that.
6. Do NOT create new files unless the task explicitly requires it.
7. If you discover work outside scope, note it but do not act on it.
"""


def resolve_model(model_str: str) -> str:
    return MODEL_MAP.get(model_str, model_str)


def build_prompt(root: Path, task_art) -> str:
    parts: list[str] = []

    plan_id = clean_string(task_art.metadata.get("plan"))
    chunk_id = clean_string(task_art.metadata.get("chunk"))

    if plan_id:
        plan = find_by_id(root, plan_id)
        if plan:
            parts.append(
                f"## Plan: {plan.metadata.get('title')}\n\n"
                f"Status: {plan.metadata.get('status')}\n\n"
                f"{_truncate(plan.body, 3000)}"
            )

    if chunk_id:
        chunk = find_by_id(root, chunk_id)
        if chunk:
            parts.append(
                f"## Chunk: {chunk.metadata.get('title')}\n\n"
                f"{chunk.body}"
            )

    task_meta_yaml = dump_simple_yaml(task_art.metadata).strip()
    parts.append(
        f"## YOUR TASK: {task_art.metadata.get('title')}\n\n"
        f"```yaml\n{task_meta_yaml}\n```\n\n"
        f"{task_art.body}"
    )

    return "\n\n---\n\n".join(parts)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated for context window ...]"


def get_ordered_tasks(root: Path, chunk_id: str, from_task: str | None = None) -> list[str]:
    artifacts = collect_artifacts(root)
    tasks = [
        a for a in artifacts
        if a.metadata.get("type") == "task"
        and a.metadata.get("chunk") == chunk_id
        and a.metadata.get("status") in ("open", "in_progress")
    ]

    task_by_id = {str(a.metadata["id"]): a for a in tasks}

    # Topological sort respecting depends_on
    ordered: list[str] = []
    visited: set[str] = set()

    def visit(tid: str) -> None:
        if tid in visited or tid not in task_by_id:
            return
        visited.add(tid)
        deps = task_by_id[tid].metadata.get("depends_on", [])
        if isinstance(deps, str):
            deps = [d.strip() for d in deps.split(",") if d.strip()]
        for dep in deps or []:
            visit(dep)
        ordered.append(tid)

    for tid in sorted(task_by_id.keys()):
        visit(tid)

    if from_task:
        try:
            idx = ordered.index(from_task)
            ordered = ordered[idx:]
        except ValueError:
            print(f"Warning: {from_task} not found in open tasks, starting from beginning")

    return ordered


def run_task(root: Path, task_id: str, dry_run: bool = False) -> bool:
    task = must_find_by_id(root, task_id)
    model = resolve_model(clean_string(task.metadata.get("model")) or "sonnet")
    prompt = build_prompt(root, task)
    title = task.metadata.get("title", "")

    print(f"\n{'=' * 70}")
    print(f"  TASK: {task_id} — {title}")
    print(f"  MODEL: {model}")
    print(f"{'=' * 70}")

    if dry_run:
        print(f"\n[DRY RUN] Prompt length: {len(prompt)} chars")
        print(f"[DRY RUN] Would run: claude --model {model} -p <prompt>")
        print(f"\n--- PROMPT PREVIEW (first 500 chars) ---")
        print(prompt[:500])
        print("--- END PREVIEW ---\n")
        return True

    # Mark in_progress
    update_artifact_status(root, task, "in_progress")

    cmd = [
        "claude",
        "--model", model,
        "-p", prompt,
        "--system-prompt", TASK_SYSTEM_PROMPT,
        "--permission-mode", "auto",
        "--max-budget-usd", "5",
        "--verbose",
    ]

    print(f"\n  Running claude --model {model} ...\n")
    result = subprocess.run(cmd, cwd=root, check=False)

    if result.returncode != 0:
        print(f"\n  *** TASK {task_id} FAILED (exit {result.returncode}) ***")
        print(f"  Fix the issue, then re-run with: python scripts/run-chunk.py {task.metadata.get('chunk')} --from {task_id}")
        return False

    # Commit changes
    subprocess.run(["git", "add", "-A"], cwd=root, check=False)
    commit_msg = f"onward: completed {task_id} — {title}"
    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_msg, "--allow-empty"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if commit_result.returncode == 0:
        print(f"  Committed: {commit_msg}")
    else:
        print(f"  Commit note: {commit_result.stdout.strip() or commit_result.stderr.strip()}")

    # Mark completed
    task = must_find_by_id(root, task_id)
    update_artifact_status(root, task, "completed")
    print(f"\n  *** TASK {task_id} COMPLETED ***")
    return True


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    chunk_id = args[0]
    dry_run = "--dry-run" in args
    from_task = None
    if "--from" in args:
        idx = args.index("--from")
        if idx + 1 < len(args):
            from_task = args[idx + 1]

    root = ROOT
    os.chdir(root)

    task_ids = get_ordered_tasks(root, chunk_id, from_task)

    if not task_ids:
        print(f"No open tasks in {chunk_id}")
        return

    print(f"\n  Chunk {chunk_id}: {len(task_ids)} task(s) to execute\n")
    for i, tid in enumerate(task_ids, 1):
        task = must_find_by_id(root, tid)
        model = resolve_model(clean_string(task.metadata.get("model")) or "sonnet")
        deps = task.metadata.get("depends_on", [])
        dep_str = f" (depends on: {', '.join(deps)})" if deps else ""
        print(f"  {i}. {tid} [{model}] {task.metadata.get('title')}{dep_str}")

    print()

    if dry_run:
        print("  --- DRY RUN MODE ---\n")

    # Mark chunk in_progress
    if not dry_run:
        chunk = must_find_by_id(root, chunk_id)
        if chunk.metadata.get("status") in ("open",):
            update_artifact_status(root, chunk, "in_progress")

    failed = False
    completed = 0
    for tid in task_ids:
        ok = run_task(root, tid, dry_run=dry_run)
        if not ok:
            failed = True
            break
        completed += 1

    print(f"\n{'=' * 70}")
    if failed:
        print(f"  STOPPED: {completed}/{len(task_ids)} tasks completed before failure")
        print(f"  Re-run: python scripts/run-chunk.py {chunk_id} --from {task_ids[completed]}")
    elif dry_run:
        print(f"  DRY RUN: {len(task_ids)} tasks previewed")
    else:
        # Complete the chunk
        chunk = must_find_by_id(root, chunk_id)
        if chunk.metadata.get("status") in ("open", "in_progress"):
            update_artifact_status(root, chunk, "completed")
        print(f"  CHUNK {chunk_id} COMPLETED ({completed} tasks)")

        subprocess.run(["git", "add", "-A"], cwd=root, check=False)
        subprocess.run(
            ["git", "commit", "-m", f"onward: chunk {chunk_id} completed", "--allow-empty"],
            cwd=root, capture_output=True, check=False,
        )
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
