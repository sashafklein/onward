"""Executor availability checks before subprocess-backed runs."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from onward.config import is_executor_enabled
from onward.util import clean_string

# Shell builtins / test stubs: do not require PATH resolution (e.g. Windows without `true`).
_SKIP_PREFLIGHT_COMMANDS = frozenset({"true", "false"})


def _executor_command(config: dict[str, Any]) -> str:
    block = config.get("executor", {})
    if not isinstance(block, dict):
        block = {}
    return clean_string(block.get("command")) or "onward-exec"


def _first_invocation_token(command: str) -> str:
    command = command.strip()
    if not command:
        return "onward-exec"
    return command.split(None, 1)[0]


def _is_explicit_path(token: str) -> bool:
    if token.startswith(("/", "./", "../")):
        return True
    if os.name == "nt" and len(token) >= 2 and token[1] == ":":
        return True
    if os.name == "nt" and token.startswith("\\\\"):
        return True
    try:
        return Path(token).expanduser().is_absolute()
    except OSError:
        return False


def preflight_shell_invocation(command_line: str) -> str | None:
    """Verify the first token of ``command_line`` is invokable (PATH or executable file).

    Used for any subprocess argv0 (global ``executor.command`` or per-review override).
    Returns ``None`` when checks pass or are skipped. Otherwise a single-line,
    actionable error message (no ``Error:`` prefix).
    """
    command_line = clean_string(command_line)
    if not command_line:
        return "executor command is empty"

    token = _first_invocation_token(command_line)
    if token.lower() in _SKIP_PREFLIGHT_COMMANDS:
        return None

    if _is_explicit_path(token):
        path = Path(token).expanduser()
        if not path.is_file():
            return f"executor command path does not exist: {token!r}"
        if not os.access(path, os.X_OK):
            return f"executor command is not executable: {token!r}"
        return None

    resolved = shutil.which(token)
    if resolved is None:
        return (
            f"executor command not found on PATH: {token!r} "
            f"(install it, use a full path in config, or for tests use command \"true\")"
        )
    return None


def preflight_executor_command(config: dict[str, Any]) -> str | None:
    """If ``executor.enabled`` is true, verify the configured executor is invokable.

    Returns ``None`` when checks pass or are skipped. Otherwise a single-line,
    actionable error message (no ``Error:`` prefix).
    """
    if not is_executor_enabled(config):
        return None

    command = _executor_command(config)
    err = preflight_shell_invocation(command)
    if err is None:
        return None
    token = _first_invocation_token(command)
    if "does not exist" in err:
        return (
            f"executor command path does not exist: {token!r} "
            f"(executor.command in .onward.config.yaml)"
        )
    if "not executable" in err:
        return f"executor command is not executable: {token!r}"
    return (
        f"executor command not found on PATH: {token!r} "
        f"(install it, use a full path in executor.command, or for tests use command \"true\")"
    )
