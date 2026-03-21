"""Unit tests for WorkReporter output formatting."""
from __future__ import annotations

import io
import os
import threading
from unittest.mock import patch

import pytest

from onward.reporter import WorkReporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture(reporter: WorkReporter, method: str, *args, **kwargs) -> str:
    """Call reporter.<method>(*args) and return the printed line (no trailing newline)."""
    buf = io.StringIO()
    with patch("builtins.print", side_effect=lambda s: buf.write(s + "\n")):
        getattr(reporter, method)(*args, **kwargs)
    return buf.getvalue().rstrip("\n")


# ---------------------------------------------------------------------------
# color=False — symbol and format correctness
# ---------------------------------------------------------------------------


def test_status_change_format() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "status_change", "TASK-001", "My task title", "in_progress")
    assert "▸" in line
    assert "TASK-001" in line
    assert "→" in line
    assert "in_progress" in line
    assert '"My task title"' in line


def test_working_on_format() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "working_on", "TASK-002", "Do the thing")
    assert "●" in line
    assert "Working on" in line
    assert "TASK-002" in line
    assert '"Do the thing"' in line


def test_completed_format() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "completed", "CHUNK-001", "First chunk")
    assert "✓" in line
    assert "CHUNK-001" in line
    assert "completed" in line
    assert '"First chunk"' in line


def test_failed_format_without_reason() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "failed", "TASK-003", "Broken task")
    assert "✗" in line
    assert "TASK-003" in line
    assert "failed" in line
    assert '"Broken task"' in line


def test_failed_format_with_reason() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "failed", "TASK-003", "Broken task", "executor exited 1")
    assert "executor exited 1" in line


def test_skipped_format_without_reason() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "skipped", "TASK-004", "Already done")
    assert "⊘" in line
    assert "TASK-004" in line
    assert "skipped" in line
    assert '"Already done"' in line


def test_skipped_format_with_reason() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "skipped", "TASK-004", "Already done", "already completed")
    assert "already completed" in line


def test_warning_format() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "warning", "no chunks found")
    assert "⚠" in line
    assert "no chunks found" in line


def test_info_format() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "info", "Created follow-up task TASK-099")
    assert "Created follow-up task TASK-099" in line


# ---------------------------------------------------------------------------
# plan_summary pluralization
# ---------------------------------------------------------------------------


def test_plan_summary_singular() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "plan_summary", "PLAN-001", "My plan", 1, 1)
    assert "1 chunk," in line or "1 chunk" in line
    assert "1 task" in line
    assert "chunks" not in line
    assert "tasks" not in line


def test_plan_summary_plural() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "plan_summary", "PLAN-001", "My plan", 3, 7)
    assert "3 chunks" in line
    assert "7 tasks" in line


def test_plan_summary_mixed() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "plan_summary", "PLAN-002", "Another plan", 1, 5)
    assert "1 chunk" in line
    assert "5 tasks" in line
    assert "1 chunks" not in line


def test_plan_summary_contains_plan_id() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "plan_summary", "PLAN-007", "The plan", 2, 4)
    assert "PLAN-007" in line
    assert "✓" in line


# ---------------------------------------------------------------------------
# Indentation
# ---------------------------------------------------------------------------


def test_no_indent_by_default() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "info", "hello")
    assert line == "hello"


def test_one_level_indent() -> None:
    r = WorkReporter(color=False)
    buf = io.StringIO()
    with patch("builtins.print", side_effect=lambda s: buf.write(s + "\n")):
        with r.indent():
            r.info("indented")
    assert buf.getvalue().rstrip("\n") == "  indented"


def test_two_level_indent() -> None:
    r = WorkReporter(color=False)
    buf = io.StringIO()
    with patch("builtins.print", side_effect=lambda s: buf.write(s + "\n")):
        with r.indent():
            with r.indent():
                r.info("deep")
    assert buf.getvalue().rstrip("\n") == "    deep"


def test_indent_restores_after_exit() -> None:
    r = WorkReporter(color=False)
    lines: list[str] = []
    with patch("builtins.print", side_effect=lambda s: lines.append(s)):
        r.info("before")
        with r.indent():
            r.info("inside")
        r.info("after")
    assert lines[0] == "before"
    assert lines[1] == "  inside"
    assert lines[2] == "after"


def test_indent_restores_on_exception() -> None:
    r = WorkReporter(color=False)
    try:
        with r.indent():
            raise ValueError("boom")
    except ValueError:
        pass
    assert r._indent == 0


# ---------------------------------------------------------------------------
# Color on/off
# ---------------------------------------------------------------------------

ANSI_ESC = "\033["


def test_color_false_produces_no_ansi() -> None:
    r = WorkReporter(color=False)
    for method, args in [
        ("status_change", ("TASK-001", "title", "in_progress")),
        ("working_on", ("TASK-001", "title")),
        ("completed", ("TASK-001", "title")),
        ("failed", ("TASK-001", "title", "reason")),
        ("skipped", ("TASK-001", "title", "reason")),
        ("warning", ("msg",)),
        ("plan_summary", ("PLAN-001", "title", 2, 3)),
    ]:
        line = _capture(r, method, *args)
        assert ANSI_ESC not in line, f"{method} produced ANSI codes with color=False"


def test_color_true_produces_ansi() -> None:
    r = WorkReporter(color=True)
    line = _capture(r, "status_change", "TASK-001", "title", "in_progress")
    assert ANSI_ESC in line


def test_color_true_completed_contains_ansi() -> None:
    r = WorkReporter(color=True)
    line = _capture(r, "completed", "TASK-001", "title")
    assert ANSI_ESC in line


def test_no_color_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    # color=None triggers auto-detection; isatty will be False in test runner,
    # so we force isatty=True to confirm NO_COLOR still wins.
    with patch("sys.stdout") as mock_stdout:
        mock_stdout.isatty.return_value = True
        r = WorkReporter(color=None)
    assert r._color is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_title() -> None:
    r = WorkReporter(color=False)
    line = _capture(r, "status_change", "TASK-001", "", "open")
    assert "TASK-001" in line
    assert '""' in line


def test_special_characters_in_title() -> None:
    r = WorkReporter(color=False)
    title = 'Fix "quotes" & <angle> brackets'
    line = _capture(r, "completed", "TASK-001", title)
    assert title in line


def test_long_title() -> None:
    r = WorkReporter(color=False)
    title = "A" * 200
    line = _capture(r, "working_on", "TASK-001", title)
    assert title in line


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


def test_thread_safety_no_interleaved_lines() -> None:
    """Concurrent calls must not produce garbled/partial lines."""
    r = WorkReporter(color=False)
    collected: list[str] = []

    original_print = print

    def capturing_print(s: str) -> None:
        collected.append(s)

    n_threads = 20
    barrier = threading.Barrier(n_threads)

    def worker(i: int) -> None:
        barrier.wait()
        with patch("builtins.print", side_effect=capturing_print):
            r.info(f"message-{i:03d}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Every line must be a complete message (starts with zero or more spaces then "message-")
    assert len(collected) == n_threads
    for line in collected:
        assert line.startswith("message-"), f"garbled line: {line!r}"
