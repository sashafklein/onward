"""Built-in CLI routing, prompt parity with ``onward-exec``, and :class:`~onward.executor_builtin.BuiltinExecutor` runs."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from onward.artifacts import Artifact
from onward.executor import TaskContext
from onward.executor_ack import SUCCESS_ACK_SCHEMA_VERSION
from onward.executor_builtin import (
    BuiltinExecutor,
    CLIBackend,
    ClaudeBackend,
    CursorBackend,
    build_hook_prompt,
    build_review_prompt,
    build_task_prompt,
    model_string_matches_cli_routing_hint,
    route_model_to_backend,
    _chunk_context_lines,
    _plan_context_lines,
)


def _load_onward_exec_reference() -> Any:
    path = Path(__file__).resolve().parents[1] / "scripts" / "onward-exec"
    loader = importlib.machinery.SourceFileLoader("_onward_exec_reference", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def onward_exec_ref() -> Any:
    return _load_onward_exec_reference()


def test_route_opus_and_sonnet_to_claude() -> None:
    assert route_model_to_backend("opus-latest").name == "claude"
    assert route_model_to_backend("sonnet-4.6").name == "claude"


def test_route_cursor_and_gemini_to_cursor() -> None:
    assert route_model_to_backend("cursor-fast").name == "cursor"
    assert route_model_to_backend("gemini-2").name == "cursor"


def test_route_unknown_defaults_to_claude() -> None:
    assert route_model_to_backend("unknown-model").name == "claude"


def test_route_codex_substring_to_claude() -> None:
    assert route_model_to_backend("codex-latest").name == "claude"


def test_model_string_matches_cli_routing_hint() -> None:
    assert model_string_matches_cli_routing_hint("opus-latest")
    assert model_string_matches_cli_routing_hint("codex-latest")
    assert model_string_matches_cli_routing_hint("cursor-fast")
    assert model_string_matches_cli_routing_hint("gemini-2")
    assert not model_string_matches_cli_routing_hint("weird-custom-id")
    assert model_string_matches_cli_routing_hint("")
    assert model_string_matches_cli_routing_hint("   ")


def test_route_claude_substring_to_claude() -> None:
    assert route_model_to_backend("anthropic-claude-3").name == "claude"


def test_route_haiku_prefix_to_claude() -> None:
    assert route_model_to_backend("haiku-latest").name == "claude"


def test_route_empty_model_to_claude() -> None:
    assert route_model_to_backend("").name == "claude"
    assert route_model_to_backend("   ").name == "claude"


def test_route_case_insensitive() -> None:
    assert route_model_to_backend("OPUS-1").name == "claude"
    assert route_model_to_backend("Cursor-Fast").name == "cursor"


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("opus-latest", "claude"),
        ("sonnet-4.6", "claude"),
        ("cursor-fast", "cursor"),
        ("unknown-model", "claude"),
    ],
)
def test_route_model_to_backend_acceptance(model: str, expected: str) -> None:
    assert route_model_to_backend(model).name == expected


def test_claude_build_argv() -> None:
    argv = ClaudeBackend().build_argv("opus-latest", "do X")
    assert argv == ["claude", "--model", "opus-latest", "-p", "do X"]


def test_cursor_build_argv_uses_agent_subcommand() -> None:
    argv = CursorBackend().build_argv("cursor-fast", "do X")
    assert argv == ["cursor", "agent", "--model", "cursor-fast", "-p", "do X"]


def test_find_executable_uses_backend_name(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_which(cmd: str) -> str | None:
        calls.append(cmd)
        return f"/opt/bin/{cmd}" if cmd == "claude" else None

    monkeypatch.setattr("onward.executor_builtin.shutil.which", fake_which)
    assert ClaudeBackend().find_executable() == "/opt/bin/claude"
    assert calls == ["claude"]


def test_claude_backend_is_abstract_interface() -> None:
    assert issubclass(ClaudeBackend, CLIBackend)
    assert issubclass(CursorBackend, CLIBackend)


def test_cli_backend_abc_is_not_instantiable() -> None:
    with pytest.raises(TypeError, match="abstract"):
        CLIBackend()  # type: ignore[misc]


def _task_context_from_payload(payload: dict[str, Any]) -> TaskContext:
    task_raw = payload.get("task")
    meta = task_raw if isinstance(task_raw, dict) else {}
    plan = payload.get("plan")
    chunk = payload.get("chunk")
    return TaskContext(
        task=Artifact(
            file_path=Path("/dev/null"),
            body=str(payload.get("body", "") or ""),
            metadata=meta,
        ),
        model="opus-latest",
        run_id="run-test",
        plan_context=plan if isinstance(plan, dict) else None,
        chunk_context=chunk if isinstance(chunk, dict) else None,
        notes=payload.get("notes"),
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "task", "body": "Do the thing.", "task": {"id": "TASK-001"}},
        {
            "type": "task",
            "body": "Body only.",
            "task": {},
            "plan": None,
            "chunk": None,
            "notes": None,
        },
        {
            "type": "task",
            "body": "With notes.",
            "task": {},
            "notes": "  remember this  ",
        },
        {
            "type": "task",
            "body": "",
            "task": {},
            "plan": {
                "metadata": {"title": "P", "description": "D"},
                "body": "Plan body here.",
            },
            "chunk": {
                "metadata": {"title": "C"},
                "body": "Chunk body.",
            },
        },
        {
            "type": "task",
            "body": "Minimal plan",
            "task": {},
            "plan": {"metadata": {}, "body": ""},
        },
        {
            "type": "task",
            "body": "Title-only plan",
            "task": {},
            "plan": {"metadata": {"title": "T only"}, "body": ""},
        },
    ],
)
def test_build_task_prompt_matches_reference(
    onward_exec_ref: Any, payload: dict[str, Any]
) -> None:
    expected = onward_exec_ref.build_task_prompt(payload)
    ctx = _task_context_from_payload(payload)
    assert build_task_prompt(ctx) == expected


def test_plan_and_chunk_helpers_match_reference(onward_exec_ref: Any) -> None:
    plan = {"metadata": {"title": "T", "description": "S"}, "body": "PB"}
    chunk = {"metadata": {"title": "CT"}, "body": "CB"}
    assert _plan_context_lines(plan) == onward_exec_ref._plan_context_lines(plan)
    assert _chunk_context_lines(chunk) == onward_exec_ref._chunk_context_lines(chunk)
    assert _plan_context_lines(None) == onward_exec_ref._plan_context_lines(None)
    assert _chunk_context_lines({}) == onward_exec_ref._chunk_context_lines({})


@pytest.mark.parametrize(
    "payload",
    [
        {"hook_body": "run me", "phase": "pre_task", "task_body": "TB"},
        {"hook_body": "", "phase": "pre_task", "task_body": None},
        {
            "hook_body": "post md",
            "phase": "post_chunk_markdown",
            "chunk_body": "CHUNK\nTEXT",
        },
    ],
)
def test_build_hook_prompt_matches_reference(onward_exec_ref: Any, payload: dict[str, Any]) -> None:
    assert build_hook_prompt(payload) == onward_exec_ref.build_hook_prompt(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"prompt": "Review this."},
        {"prompt": ""},
        {"prompt": None},
    ],
)
def test_build_review_prompt_matches_reference(onward_exec_ref: Any, payload: dict[str, Any]) -> None:
    assert build_review_prompt(payload) == onward_exec_ref.build_review_prompt(payload)


class _FakePipe:
    def __init__(self, lines: list[str]) -> None:
        self._lines = list(lines)
        self._i = 0

    def readline(self) -> str:
        if self._i < len(self._lines):
            s = self._lines[self._i]
            self._i += 1
            return s if s.endswith("\n") else f"{s}\n"
        return ""

    def close(self) -> None:
        pass


class _FakeProc:
    def __init__(
        self,
        *,
        stdout_lines: list[str],
        stderr_lines: list[str],
        return_code: int = 0,
    ) -> None:
        self.stdout = _FakePipe(stdout_lines)
        self.stderr = _FakePipe(stderr_lines)
        self._return_code = return_code

    def wait(self) -> int:
        return self._return_code


def _run_ctx(tmp_path: Path, *, model: str = "opus-latest", run_id: str = "RUN-1-TASK-001") -> TaskContext:
    return TaskContext(
        task=Artifact(
            tmp_path / "TASK-001.md",
            "task body",
            {"id": "TASK-001", "title": "T"},
        ),
        model=model,
        run_id=run_id,
        plan_context=None,
        chunk_context=None,
        notes=None,
    )


def test_builtin_executor_is_executor_subclass() -> None:
    from onward.executor import Executor

    assert issubclass(BuiltinExecutor, Executor)


@patch("onward.executor_builtin.subprocess.Popen")
def test_builtin_spawns_claude_argv(mock_popen: MagicMock, tmp_path: Path) -> None:
    mock_popen.return_value = _FakeProc(stdout_lines=["ok\n"], stderr_lines=[])
    monkey_exe = "/x/claude"
    ctx = _run_ctx(tmp_path)
    expected_prompt = build_task_prompt(ctx)

    def fake_which(name: str) -> str | None:
        return monkey_exe if name == "claude" else None

    with patch("onward.executor_builtin.shutil.which", fake_which):
        ex = BuiltinExecutor({})
        r = ex.execute_task(tmp_path, ctx)

    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    argv = args[0]
    assert argv == [monkey_exe, "--model", "opus-latest", "-p", expected_prompt]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["text"] is True
    assert kwargs["env"]["ONWARD_RUN_ID"] == "RUN-1-TASK-001"
    assert r.success
    assert r.return_code == 0
    assert "ok" in r.output


@patch("onward.executor_builtin.subprocess.Popen")
def test_builtin_spawns_cursor_argv(mock_popen: MagicMock, tmp_path: Path) -> None:
    mock_popen.return_value = _FakeProc(stdout_lines=[], stderr_lines=[])
    monkey_exe = "/x/cursor"

    def fake_which(name: str) -> str | None:
        return monkey_exe if name == "cursor" else None

    with patch("onward.executor_builtin.shutil.which", fake_which):
        ex = BuiltinExecutor({})
        ex.execute_task(tmp_path, _run_ctx(tmp_path, model="cursor-fast"))

    argv = mock_popen.call_args[0][0]
    assert argv[0] == monkey_exe
    assert argv[1:5] == ["agent", "--model", "cursor-fast", "-p"]
    assert argv[5] == build_task_prompt(_run_ctx(tmp_path, model="cursor-fast"))


def test_builtin_missing_cli_no_popen(tmp_path: Path) -> None:
    with patch("onward.executor_builtin.shutil.which", lambda _n: None):
        ex = BuiltinExecutor({})
        r = ex.execute_task(tmp_path, _run_ctx(tmp_path))
    assert not r.success
    assert r.return_code == -1
    assert "not found" in r.error.lower()
    assert r.output == ""


@patch("onward.executor_builtin.subprocess.Popen")
def test_builtin_parses_ack(mock_popen: MagicMock, tmp_path: Path) -> None:
    line = json.dumps(
        {
            "onward_task_result": {
                "status": "completed",
                "schema_version": SUCCESS_ACK_SCHEMA_VERSION,
                "run_id": "RUN-1-TASK-001",
            }
        }
    )
    mock_popen.return_value = _FakeProc(stdout_lines=["x\n", f"{line}\n"], stderr_lines=[])

    with patch("onward.executor_builtin.shutil.which", lambda _n: "/bin/claude"):
        r = BuiltinExecutor({}).execute_task(tmp_path, _run_ctx(tmp_path))

    assert r.success
    assert r.ack is not None
    assert r.ack["onward_task_result"]["status"] == "completed"


@patch("onward.executor_builtin.subprocess.Popen")
def test_builtin_require_ack_fails(mock_popen: MagicMock, tmp_path: Path) -> None:
    mock_popen.return_value = _FakeProc(stdout_lines=["no json\n"], stderr_lines=[])
    cfg = {"work": {"require_success_ack": True}}

    with patch("onward.executor_builtin.shutil.which", lambda _n: "/bin/claude"):
        r = BuiltinExecutor(cfg).execute_task(tmp_path, _run_ctx(tmp_path))

    assert not r.success
    assert "onward_task_result" in r.error


@patch("onward.executor_builtin.subprocess.Popen")
def test_builtin_nonzero_exit(mock_popen: MagicMock, tmp_path: Path) -> None:
    mock_popen.return_value = _FakeProc(stdout_lines=[], stderr_lines=["e\n"], return_code=3)

    with patch("onward.executor_builtin.shutil.which", lambda _n: "/bin/claude"):
        r = BuiltinExecutor({}).execute_task(tmp_path, _run_ctx(tmp_path))

    assert not r.success
    assert r.return_code == 3
    assert "code 3" in r.error


@patch("onward.executor_builtin.subprocess.Popen", side_effect=OSError("nope"))
def test_builtin_popen_oserror(mock_popen: MagicMock, tmp_path: Path) -> None:
    with patch("onward.executor_builtin.shutil.which", lambda _n: "/bin/claude"):
        r = BuiltinExecutor({}).execute_task(tmp_path, _run_ctx(tmp_path))
    assert not r.success
    assert "nope" in r.error
    assert r.return_code == -1


@patch("onward.executor_builtin.subprocess.Popen")
def test_builtin_streams_to_stdout(
    mock_popen: MagicMock,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    mock_popen.return_value = _FakeProc(stdout_lines=["visible\n"], stderr_lines=["errl\n"])

    with patch("onward.executor_builtin.shutil.which", lambda _n: "/bin/claude"):
        BuiltinExecutor({}).execute_task(tmp_path, _run_ctx(tmp_path))

    out, err = capsys.readouterr()
    assert "visible" in out
    assert "errl" in err
