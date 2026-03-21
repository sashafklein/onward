"""Built-in CLI backends: map model strings to Claude Code vs Cursor Agent invocations."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from onward.config import work_require_success_ack
from onward.executor_ack import find_task_success_ack

if TYPE_CHECKING:
    from onward.executor import TaskContext


class CLIBackend(ABC):
    """Executable + argv shape for a provider CLI."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier (e.g. ``claude``, ``cursor``)."""

    @abstractmethod
    def build_argv(self, model: str, prompt: str) -> list[str]:
        """Argv with the program name as ``argv[0]`` (may be replaced by :meth:`find_executable`)."""

    def find_executable(self) -> str | None:
        """Resolve ``argv[0]`` on ``PATH`` via :func:`shutil.which`."""
        return shutil.which(self.name)


class ClaudeBackend(CLIBackend):
    """Anthropic Claude Code CLI: ``claude --model <m> -p <prompt>``."""

    @property
    def name(self) -> str:
        return "claude"

    def build_argv(self, model: str, prompt: str) -> list[str]:
        return ["claude", "--model", model, "-p", prompt]


class CursorBackend(CLIBackend):
    """Cursor Agent via ``cursor`` binary: ``cursor agent --model <m> -p <prompt>``.

    Cursor exposes agent mode as the ``agent`` subcommand (not a ``--agent`` flag).
    """

    @property
    def name(self) -> str:
        return "cursor"

    def build_argv(self, model: str, prompt: str) -> list[str]:
        return ["cursor", "agent", "--model", model, "-p", prompt]


# Stateless backends — reuse one instance each.
_CLAUDE_SINGLETON: ClaudeBackend | None = None
_CURSOR_SINGLETON: CursorBackend | None = None


def _claude_backend() -> ClaudeBackend:
    global _CLAUDE_SINGLETON
    if _CLAUDE_SINGLETON is None:
        _CLAUDE_SINGLETON = ClaudeBackend()
    return _CLAUDE_SINGLETON


def _cursor_backend() -> CursorBackend:
    global _CURSOR_SINGLETON
    if _CURSOR_SINGLETON is None:
        _CURSOR_SINGLETON = CursorBackend()
    return _CURSOR_SINGLETON


def route_model_to_backend(model: str) -> CLIBackend:
    """Pick a backend from the model id string (case-insensitive).

    Rules (first match): substring ``claude`` / ``codex`` → Claude; prefixes ``opus`` /
    ``sonnet`` / ``haiku`` → Claude; substring ``cursor`` → Cursor; substring ``gemini`` → Cursor;
    otherwise Claude.
    """
    m = (model or "").strip().lower()
    if not m:
        return _claude_backend()
    if "claude" in m:
        return _claude_backend()
    if "codex" in m:
        return _claude_backend()
    if m.startswith("opus") or m.startswith("sonnet") or m.startswith("haiku"):
        return _claude_backend()
    if "cursor" in m:
        return _cursor_backend()
    if "gemini" in m:
        return _cursor_backend()
    return _claude_backend()


def model_string_matches_cli_routing_hint(model: str) -> bool:
    """True when ``model`` matches an explicit built-in routing rule (not the generic Claude fallback).

    Used by ``onward doctor`` to surface model ids that rely on the default Claude CLI path
    without matching a known substring/prefix pattern.
    """
    m = (model or "").strip().lower()
    if not m:
        return True
    if "claude" in m or "codex" in m:
        return True
    if m.startswith("opus") or m.startswith("sonnet") or m.startswith("haiku"):
        return True
    if "cursor" in m or "gemini" in m:
        return True
    return False


def _plan_context_lines(plan: dict[str, Any] | None) -> list[str]:
    if not plan or not isinstance(plan, dict):
        return []
    meta = plan.get("metadata") if isinstance(plan.get("metadata"), dict) else {}
    title = str(meta.get("title", "")).strip()
    body = str(plan.get("body", "")).strip()
    lines: list[str] = ["## Plan context"]
    if title:
        lines.append(f"Title: {title}")
    summary = str(meta.get("description", "")).strip()
    if summary:
        lines.append(f"Summary: {summary}")
    if body:
        lines.append("")
        lines.append(body)
    return lines if len(lines) > 1 else []


def _chunk_context_lines(chunk: dict[str, Any] | None) -> list[str]:
    if not chunk or not isinstance(chunk, dict):
        return []
    meta = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    title = str(meta.get("title", "")).strip()
    body = str(chunk.get("body", "")).strip()
    lines: list[str] = ["## Chunk context"]
    if title:
        lines.append(f"Title: {title}")
    if body:
        lines.append("")
        lines.append(body)
    return lines if len(lines) > 1 else []


def build_task_prompt(ctx: "TaskContext") -> str:
    """Build the task prompt from :class:`~onward.executor.TaskContext` (same text as ``onward-exec``)."""
    parts: list[str] = []
    plan = ctx.plan_context
    chunk = ctx.chunk_context
    parts.extend(_plan_context_lines(plan if isinstance(plan, dict) else None))
    parts.extend(_chunk_context_lines(chunk if isinstance(chunk, dict) else None))
    parts.append("## Task")
    parts.append(str(ctx.task.body or "").strip())
    notes = ctx.notes
    if notes and str(notes).strip():
        parts.append("")
        parts.append("## Notes")
        parts.append(str(notes).strip())
    parts.append("")
    parts.append(
        "---\nWhen finished, ensure your final output reflects completion of the task "
        "as described above."
    )
    return "\n\n".join(p for p in parts if p).strip() + "\n"


def build_hook_prompt(payload: dict[str, Any]) -> str:
    """Build hook-phase prompt from executor stdin payload (matches ``scripts/onward-exec``)."""
    hook = str(payload.get("hook_body", "") or "").strip()
    phase = str(payload.get("phase", ""))
    parts = [f"# Hook ({phase})", "", hook]
    if payload.get("phase") == "post_chunk_markdown":
        cb = payload.get("chunk_body")
        if cb:
            parts.extend(["", "## Chunk body", str(cb)])
    else:
        tb = payload.get("task_body")
        if tb:
            parts.extend(["", "## Task body", str(tb)])
    return "\n".join(parts).strip() + "\n"


def build_review_prompt(payload: dict[str, Any]) -> str:
    """Build review prompt from executor stdin payload (matches ``scripts/onward-exec``)."""
    return str(payload.get("prompt", "") or "").strip() + "\n"


def _combined_task_output(stdout: str, stderr: str) -> str:
    """Match :class:`~onward.executor.SubprocessExecutor` stream formatting for run logs."""
    output = stdout.rstrip()
    if stderr.strip():
        stderr_block = stderr.rstrip()
        output = (
            f"{output}\n\n[task stderr]\n{stderr_block}" if output else f"[task stderr]\n{stderr_block}"
        )
    return output


def _tee_stream(
    pipe: Any,
    tee_to: TextIO,
    buffer: list[str],
    file_out: TextIO | None = None,
    file_lock: threading.Lock | None = None,
) -> None:
    try:
        for line in iter(pipe.readline, ""):
            buffer.append(line)
            tee_to.write(line)
            tee_to.flush()
            if file_out is not None:
                if file_lock is not None:
                    with file_lock:
                        file_out.write(line)
                        file_out.flush()
                else:
                    file_out.write(line)
                    file_out.flush()
    finally:
        pipe.close()


def extract_token_usage(stderr_output: str) -> dict[str, Any] | None:
    """Parse token usage from Claude CLI stderr output (best-effort; returns None on failure)."""
    import json as _json
    import re as _re

    try:
        lines = stderr_output.strip().splitlines()
        for line in reversed(lines):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = _json.loads(stripped)
                if isinstance(obj, dict):
                    for usage_key in ("usage", "token_usage"):
                        usage = obj.get(usage_key)
                        if isinstance(usage, dict):
                            inp = usage.get("input_tokens") or usage.get("input")
                            out = usage.get("output_tokens") or usage.get("output")
                            if inp is not None or out is not None:
                                result: dict[str, Any] = {}
                                if inp is not None:
                                    result["input_tokens"] = int(inp)
                                if out is not None:
                                    result["output_tokens"] = int(out)
                                if "input_tokens" in result and "output_tokens" in result:
                                    result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
                                return result
            except (ValueError, TypeError):
                pass

        for line in reversed(lines):
            m = _re.search(
                r"input[_ ]tokens?[:\s]+(\d+)[,\s]+output[_ ]tokens?[:\s]+(\d+)",
                line,
                _re.IGNORECASE,
            )
            if m:
                inp_tok = int(m.group(1))
                out_tok = int(m.group(2))
                return {
                    "input_tokens": inp_tok,
                    "output_tokens": out_tok,
                    "total_tokens": inp_tok + out_tok,
                }
    except Exception:  # noqa: BLE001
        pass
    return None


from onward.executor import Executor, ExecutorResult  # noqa: E402 — circular import; executor finishes ABCs first


class BuiltinExecutor(Executor):
    """Run tasks via Claude Code or Cursor agent CLI with streamed stdout/stderr."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._require_success_ack = work_require_success_ack(config)

    def execute_task(self, root: Path, ctx: "TaskContext") -> ExecutorResult:
        task_id = str(ctx.task.metadata.get("id", ""))
        run_id = ctx.run_id
        prompt = build_task_prompt(ctx)
        backend = route_model_to_backend(ctx.model)
        exe = backend.find_executable()
        if not exe:
            return ExecutorResult(
                task_id=task_id,
                run_id=run_id,
                success=False,
                output="",
                error=f"'{backend.name}' not found on PATH",
                ack=None,
                return_code=-1,
            )

        argv = [exe, *backend.build_argv(ctx.model, prompt)[1:]]
        child_env = {**os.environ, "ONWARD_RUN_ID": run_id}
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        output_log_path = ctx.output_log
        output_log_handle: Any = None
        file_lock: threading.Lock | None = None

        try:
            proc = subprocess.Popen(
                argv,
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=child_env,
            )
        except OSError as exc:
            return ExecutorResult(
                task_id=task_id,
                run_id=run_id,
                success=False,
                output="",
                error=str(exc),
                ack=None,
                return_code=-1,
            )

        if output_log_path is not None:
            try:
                output_log_path.touch()
                output_log_handle = output_log_path.open("w", encoding="utf-8")
                file_lock = threading.Lock()
            except OSError:
                output_log_handle = None
                file_lock = None

        try:
            assert proc.stdout is not None and proc.stderr is not None
            t_out = threading.Thread(
                target=_tee_stream,
                args=(proc.stdout, sys.stdout, stdout_chunks),
                kwargs={"file_out": output_log_handle, "file_lock": file_lock},
                daemon=True,
            )
            t_err = threading.Thread(
                target=_tee_stream,
                args=(proc.stderr, sys.stderr, stderr_chunks),
                kwargs={"file_out": output_log_handle, "file_lock": file_lock},
                daemon=True,
            )
            t_out.start()
            t_err.start()
            return_code = int(proc.wait())
            t_out.join()
            t_err.join()
        finally:
            if output_log_handle is not None:
                try:
                    output_log_handle.close()
                except OSError:
                    pass

        stdout_text = "".join(stdout_chunks)
        stderr_text = "".join(stderr_chunks)
        output = _combined_task_output(stdout_text, stderr_text)

        ok = return_code == 0
        error = ""
        ack_obj: dict[str, Any] | None = None
        if ok:
            found, ack_err, ack_obj = find_task_success_ack(stdout_text, stderr_text, run_id)
            if self._require_success_ack and not found:
                ok = False
                error = ack_err
        else:
            error = f"executor exited with code {return_code}"

        cli_usage = extract_token_usage(stderr_text)
        ack_usage: dict[str, Any] | None = None
        if ack_obj is not None:
            otr = ack_obj.get("onward_task_result")
            if isinstance(otr, dict):
                raw_usage = otr.get("token_usage")
                if isinstance(raw_usage, dict):
                    ack_usage = raw_usage
        token_usage = ack_usage if ack_usage is not None else cli_usage

        return ExecutorResult(
            task_id=task_id,
            run_id=run_id,
            success=ok,
            output=output,
            error=error,
            ack=ack_obj,
            return_code=return_code,
            token_usage=token_usage,
        )
