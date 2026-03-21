from __future__ import annotations

import os
import sys
import threading
from contextlib import contextmanager
from typing import Iterator

from onward.util import _colorize, _status_color


class WorkReporter:
    def __init__(self, color: bool | None = None) -> None:
        if color is None:
            color = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
        self._color = color
        self._indent = 0
        self._lock = threading.Lock()

    def _write(self, line: str) -> None:
        prefix = "  " * self._indent
        with self._lock:
            print(f"{prefix}{line}")

    def _c(self, text: str, color: str) -> str:
        return _colorize(text, color, self._color)

    @contextmanager
    def indent(self) -> Iterator[None]:
        self._indent += 1
        try:
            yield
        finally:
            self._indent -= 1

    def status_change(self, artifact_id: str, title: str, new_status: str) -> None:
        symbol = self._c("\u25b8", "bold")
        status_str = self._c(new_status, _status_color(new_status))
        id_str = self._c(artifact_id, "bold")
        self._write(f'{symbol} {id_str} \u2192 {status_str}  "{title}"')

    def working_on(self, artifact_id: str, title: str) -> None:
        symbol = self._c("\u25cf", "blue")
        id_str = self._c(artifact_id, "bold")
        self._write(f'{symbol} Working on {id_str}  "{title}"')

    def completed(self, artifact_id: str, title: str) -> None:
        symbol = self._c("\u2713", "green")
        id_str = self._c(artifact_id, "bold")
        self._write(f'{symbol} {id_str} completed  "{title}"')

    def failed(self, artifact_id: str, title: str, reason: str = "") -> None:
        symbol = self._c("\u2717", "red")
        id_str = self._c(artifact_id, "bold")
        line = f'{symbol} {id_str} failed  "{title}"'
        if reason:
            line += f"  {self._c(reason, 'red')}"
        self._write(line)

    def skipped(self, artifact_id: str, title: str, reason: str = "") -> None:
        symbol = self._c("\u2298", "magenta")
        id_str = self._c(artifact_id, "bold")
        line = f'{symbol} {id_str} skipped  "{title}"'
        if reason:
            line += f"  {reason}"
        self._write(line)

    def plan_summary(self, plan_id: str, title: str, chunks: int, tasks: int) -> None:
        symbol = self._c("\u2713", "green")
        id_str = self._c(plan_id, "bold")
        chunk_word = "chunk" if chunks == 1 else "chunks"
        task_word = "task" if tasks == 1 else "tasks"
        self._write(f"{symbol} {id_str} completed ({chunks} {chunk_word}, {tasks} {task_word})")

    def info(self, msg: str) -> None:
        self._write(msg)

    def warning(self, msg: str) -> None:
        symbol = self._c("\u26a0", "yellow")
        self._write(f"{symbol} {msg}")
