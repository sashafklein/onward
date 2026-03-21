"""Shared helpers for CLI tests (non-production)."""

from __future__ import annotations

import re
from pathlib import Path


def set_artifact_status_in_frontmatter(artifact_path: Path, status: str) -> None:
    """Set the top-level ``status`` field in artifact frontmatter (tests only)."""
    text = artifact_path.read_text(encoding="utf-8")
    text_new = re.sub(
        r"(?m)^status:\s*\"[^\"]*\"",
        f'status: "{status}"',
        text,
        count=1,
    )
    if text_new == text:
        raise ValueError(f"no status: field found in {artifact_path}")
    artifact_path.write_text(text_new, encoding="utf-8")


def clear_post_task_shell(root: Path) -> None:
    """Remove default git commit hook so test workspaces without git still pass."""
    cfg = root / ".onward.config.yaml"
    text = cfg.read_text(encoding="utf-8")
    start = text.index("  post_task_shell:")
    end = text.index("  post_task_markdown:", start)
    cfg.write_text(text[:start] + "  post_task_shell: []\n" + text[end:], encoding="utf-8")


def clear_post_task_markdown(root: Path) -> None:
    """Disable default post-task markdown hook (requires subprocess executor / onward-exec)."""
    cfg = root / ".onward.config.yaml"
    text = cfg.read_text(encoding="utf-8")
    text = text.replace(
        "  post_task_markdown: .onward/hooks/post-task.md",
        "  post_task_markdown: null",
    )
    cfg.write_text(text, encoding="utf-8")


def clear_post_chunk_markdown(root: Path) -> None:
    """Disable default post-chunk markdown hook (same subprocess requirement as post-task)."""
    cfg = root / ".onward.config.yaml"
    text = cfg.read_text(encoding="utf-8")
    text = text.replace(
        "  post_chunk_markdown: .onward/hooks/post-chunk.md",
        "  post_chunk_markdown: null",
    )
    cfg.write_text(text, encoding="utf-8")
