"""Shared helpers for CLI tests (non-production)."""

from __future__ import annotations

from pathlib import Path


def clear_post_task_shell(root: Path) -> None:
    """Remove default git commit hook so test workspaces without git still pass."""
    cfg = root / ".onward.config.yaml"
    text = cfg.read_text(encoding="utf-8")
    start = text.index("  post_task_shell:")
    end = text.index("  pre_task_markdown:", start)
    cfg.write_text(text[:start] + "  post_task_shell: []\n" + text[end:], encoding="utf-8")
