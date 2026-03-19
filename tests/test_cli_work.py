from pathlib import Path

from onward import cli


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def _set_executor(root: Path, command: str) -> None:
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    raw = raw.replace("  command: ralph", f'  command: "{command}"')
    config_path.write_text(raw, encoding="utf-8")


def _set_hook_value(root: Path, key: str, replacement: str) -> None:
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    raw = raw.replace(f"  {key}: []", replacement)
    raw = raw.replace(f"  {key}: null", replacement)
    raw = raw.replace(f"  {key}: .onward/hooks/post-task.md", replacement)
    raw = raw.replace(f"  {key}: .onward/hooks/post-chunk.md", replacement)
    config_path.write_text(raw, encoding="utf-8")


def test_work_task_success_creates_run_and_completes_task(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Run RUN-" in out
    assert "completed" in out

    task_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-001-ship.md").read_text(encoding="utf-8")
    assert 'status: "completed"' in task_raw

    run_jsons = list((tmp_path / ".onward/runs").glob("RUN-*-TASK-001.json"))
    assert len(run_jsons) == 1
    run_raw = run_jsons[0].read_text(encoding="utf-8")
    assert 'status: "completed"' in run_raw

    ongoing = (tmp_path / ".onward/ongoing.json").read_text(encoding="utf-8")
    assert '"active_runs": []' in ongoing


def test_work_task_failure_records_failed_run_and_reopens_task(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "false")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Run RUN-" in out
    assert "failed" in out

    task_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-001-ship.md").read_text(encoding="utf-8")
    assert 'status: "open"' in task_raw

    run_jsons = list((tmp_path / ".onward/runs").glob("RUN-*-TASK-001.json"))
    assert len(run_jsons) == 1
    run_raw = run_jsons[0].read_text(encoding="utf-8")
    assert 'status: "failed"' in run_raw


def test_work_chunk_executes_ready_tasks_in_dependency_order(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "One"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Two"]) == 0
    capsys.readouterr()

    task_two = tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-002-two.md"
    raw = task_two.read_text(encoding="utf-8")
    task_two.write_text(raw.replace("depends_on: []", "depends_on:\n  - TASK-001"), encoding="utf-8")

    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.count("Run RUN-") == 2
    assert "Chunk CHUNK-001 completed" in out

    chunk_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/chunks/CHUNK-001-build.md").read_text(encoding="utf-8")
    assert 'status: "completed"' in chunk_raw

    task_one_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-001-one.md").read_text(encoding="utf-8")
    task_two_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-002-two.md").read_text(encoding="utf-8")
    assert 'status: "completed"' in task_one_raw
    assert 'status: "completed"' in task_two_raw


def test_work_task_runs_pre_and_post_shell_hooks(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    _set_hook_value(tmp_path, "pre_task_shell", '  pre_task_shell:\n    - "echo pre > .onward/pre-hook.txt"')
    _set_hook_value(tmp_path, "post_task_shell", '  post_task_shell:\n    - "echo post > .onward/post-hook.txt"')
    _set_hook_value(tmp_path, "post_task_markdown", "  post_task_markdown: null")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    capsys.readouterr()
    assert code == 0
    assert (tmp_path / ".onward/pre-hook.txt").exists()
    assert (tmp_path / ".onward/post-hook.txt").exists()


def test_work_task_fails_when_post_task_shell_hook_fails(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    _set_hook_value(tmp_path, "post_task_shell", '  post_task_shell:\n    - "exit 7"')
    _set_hook_value(tmp_path, "post_task_markdown", "  post_task_markdown: null")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "failed" in out
    task_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-001-ship.md").read_text(encoding="utf-8")
    assert 'status: "open"' in task_raw


def test_show_task_includes_latest_run_info(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    assert cli.main(["show", "--root", str(tmp_path), "TASK-001"]) == 0
    out = capsys.readouterr().out
    assert "Latest run:" in out
    assert "RUN-" in out
    assert "status: completed" in out
    assert "log:" in out


def test_show_task_without_runs_omits_run_section(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    assert cli.main(["show", "--root", str(tmp_path), "TASK-001"]) == 0
    out = capsys.readouterr().out
    assert "Latest run:" not in out


def test_recent_includes_run_records(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    assert cli.main(["recent", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "RUN-" in out
    assert "\trun\t" in out


def test_executor_payload_includes_chunk_and_plan_context(tmp_path: Path, capsys, monkeypatch):
    """Verify the executor receives chunk and plan context in its stdin payload."""
    import json
    from unittest.mock import patch

    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    captured_payloads: list[dict] = []
    original_run = __import__("subprocess").run

    def capture_run(*args, **kwargs):
        if kwargs.get("input"):
            try:
                captured_payloads.append(json.loads(kwargs["input"]))
            except (json.JSONDecodeError, TypeError):
                pass
        return original_run(*args, **kwargs)

    with patch("subprocess.run", side_effect=capture_run):
        cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    capsys.readouterr()

    task_payloads = [p for p in captured_payloads if p.get("type") == "task"]
    assert task_payloads, "expected at least one task payload to be sent to executor"
    payload = task_payloads[0]
    assert payload.get("chunk") is not None
    assert payload["chunk"]["metadata"]["id"] == "CHUNK-001"
    assert payload.get("plan") is not None
    assert payload["plan"]["metadata"]["id"] == "PLAN-001"


def test_work_chunk_fails_when_post_chunk_markdown_hook_missing(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    _set_hook_value(tmp_path, "post_task_markdown", "  post_task_markdown: null")
    _set_hook_value(tmp_path, "post_chunk_markdown", "  post_chunk_markdown: .onward/hooks/missing.md")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "post hook failed" in out
    chunk_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/chunks/CHUNK-001-build.md").read_text(encoding="utf-8")
    assert 'status: "in_progress"' in chunk_raw
