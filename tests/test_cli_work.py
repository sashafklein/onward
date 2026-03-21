import json
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from onward import cli

from tests.workspace_helpers import clear_post_task_shell


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0
    clear_post_task_shell(root)


def _set_executor(root: Path, command: str) -> None:
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    raw = raw.replace("  command: onward-exec", f'  command: "{command}"')
    config_path.write_text(raw, encoding="utf-8")


def _set_require_success_ack(root: Path, value: str) -> None:
    config_path = root / ".onward.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    text = text.replace("  require_success_ack: false", f"  require_success_ack: {value}")
    config_path.write_text(text, encoding="utf-8")


def _set_python_ack_executor(root: Path) -> None:
    script = root / ".onward" / "ack_exec.py"
    script.write_text(
        'import json, os\n'
        'print(json.dumps({"onward_task_result": {"status": "completed", "schema_version": 1, '
        '"run_id": os.environ["ONWARD_RUN_ID"]}}))\n',
        encoding="utf-8",
    )
    config_path = root / ".onward.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    text = text.replace("  command: onward-exec", f"  command: {json.dumps(sys.executable)}", 1)
    text = text.replace(
        "  args: []",
        "  args:\n    - .onward/ack_exec.py\n",
        1,
    )
    config_path.write_text(text, encoding="utf-8")


def _set_python_v2_followups_executor(root: Path) -> None:
    script = root / ".onward" / "ack_exec.py"
    script.write_text(
        'import json, os\n'
        'print(json.dumps({"onward_task_result": {"status": "completed", "schema_version": 2, '
        '"run_id": os.environ["ONWARD_RUN_ID"], "summary": "done", '
        '"follow_ups": [{"title": "Follow A", "description": "Do more", "priority": "high"}]'
        "}}))\n",
        encoding="utf-8",
    )
    config_path = root / ".onward.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    text = text.replace("  command: onward-exec", f"  command: {json.dumps(sys.executable)}", 1)
    text = text.replace(
        "  args: []",
        "  args:\n    - .onward/ack_exec.py\n",
        1,
    )
    config_path.write_text(text, encoding="utf-8")


def _set_hook_value(root: Path, key: str, replacement: str) -> None:
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    raw = raw.replace(f"  {key}: []", replacement)
    raw = raw.replace(f"  {key}: null", replacement)
    raw = raw.replace(f"  {key}: .onward/hooks/post-task.md", replacement)
    raw = raw.replace(f"  {key}: .onward/hooks/post-chunk.md", replacement)
    config_path.write_text(raw, encoding="utf-8")


def test_work_require_success_ack_fails_when_exit_0_without_ack(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_require_success_ack(tmp_path, "true")
    _set_hook_value(tmp_path, "post_task_markdown", "  post_task_markdown: null")
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    capsys.readouterr()

    assert code == 1
    run_jsons = list((tmp_path / ".onward/runs/TASK-001").glob("info-*.json"))
    assert len(run_jsons) == 1
    rec = json.loads(run_jsons[0].read_text(encoding="utf-8"))
    assert rec["status"] == "failed"
    assert "missing onward_task_result" in rec["error"]

    task_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-001-ship.md").read_text(encoding="utf-8")
    assert 'status: "failed"' in task_raw
    assert "last_run_status" in task_raw


def test_work_require_success_ack_succeeds_with_executor_ack_line(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_require_success_ack(tmp_path, "true")
    _set_hook_value(tmp_path, "post_task_markdown", "  post_task_markdown: null")
    _set_python_ack_executor(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "completed" in out

    run_jsons = list((tmp_path / ".onward/runs/TASK-001").glob("info-*.json"))
    assert len(run_jsons) == 1
    rec = json.loads(run_jsons[0].read_text(encoding="utf-8"))
    assert rec["status"] == "completed"
    assert "success_ack" in rec
    assert rec["success_ack"]["onward_task_result"]["status"] == "completed"
    assert "task_result" in rec
    assert rec["task_result"]["schema_version"] == 1


def test_work_follow_ups_create_tasks(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_hook_value(tmp_path, "post_task_markdown", "  post_task_markdown: null")
    _set_python_v2_followups_executor(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Created follow-up task TASK-002" in out
    task2 = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-002-follow-a.md").read_text(encoding="utf-8")
    assert "depends_on:" in task2
    assert "TASK-001" in task2


def test_work_no_follow_ups_skips_creation(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_hook_value(tmp_path, "post_task_markdown", "  post_task_markdown: null")
    _set_python_v2_followups_executor(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "--no-follow-ups", "TASK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Created follow-up" not in out
    assert not list((tmp_path / ".onward/plans/PLAN-001-alpha/tasks").glob("TASK-002-*.md"))


def test_work_follow_ups_dedup_by_open_task_title(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_hook_value(tmp_path, "post_task_markdown", "  post_task_markdown: null")
    _set_python_v2_followups_executor(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Follow A"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "duplicate" in out.lower()
    assert "Created follow-up" not in out


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

    run_jsons = list((tmp_path / ".onward/runs/TASK-001").glob("info-*.json"))
    assert len(run_jsons) == 1
    run_raw = run_jsons[0].read_text(encoding="utf-8")
    parsed_run = json.loads(run_raw)
    assert parsed_run["status"] == "completed"
    assert parsed_run["executor"] == "true"

    ongoing = (tmp_path / ".onward/ongoing.json").read_text(encoding="utf-8")
    assert '"active_runs": []' in ongoing


def test_work_task_failure_records_failed_run_and_sets_task_failed(tmp_path: Path, capsys):
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
    assert 'status: "failed"' in task_raw
    assert "run_count: 1" in task_raw
    assert "last_run_status" in task_raw

    run_jsons = list((tmp_path / ".onward/runs/TASK-001").glob("info-*.json"))
    assert len(run_jsons) == 1
    run_raw = run_jsons[0].read_text(encoding="utf-8")
    assert json.loads(run_raw)["status"] == "failed"


def test_retry_resets_failed_task_to_open(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "false")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()
    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 1
    capsys.readouterr()

    assert cli.main(["retry", "--root", str(tmp_path), "TASK-001"]) == 0
    out = capsys.readouterr().out
    assert "failed -> open" in out

    task_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-001-ship.md").read_text(encoding="utf-8")
    assert 'status: "open"' in task_raw
    assert "run_count: 0" in task_raw


def test_retry_errors_when_task_not_failed(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["retry", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "cannot retry" in out


def test_work_task_circuit_breaker_refuses_when_run_count_at_max(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    _set_task_run_count(task_path, 3)
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "max_retries" in out
    assert "onward retry" in out


def test_work_max_retries_zero_allows_high_run_count(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_work_max_retries(tmp_path, "0")
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    _set_task_run_count(task_path, 50)
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Run RUN-" in out


def test_work_chunk_skips_circuit_broken_task_and_runs_next(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Blocked"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ready"]) == 0
    task_a = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    _set_task_run_count(task_a, 3)
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Warning:" in out
    assert "max_retries" in out
    assert out.count("Run RUN-") == 1
    task_b = next(tmp_path.glob(".onward/plans/**/tasks/TASK-002-*.md"))
    assert 'status: "completed"' in task_b.read_text(encoding="utf-8")
    assert "no task could run" in out or "Stopping chunk work" in out


def test_next_skips_failed_task_and_suggests_next_open(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "false")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "First"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Second"]) == 0
    capsys.readouterr()
    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 1
    capsys.readouterr()

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("TASK-002\ttask\topen\t")


def _set_sequential_by_default(root: Path, value: str) -> None:
    config_path = root / ".onward.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    pos = text.find("work:")
    assert pos >= 0
    head, tail = text[:pos], text[pos:]
    tail_new = re.sub(
        r"(?m)^(\s+sequential_by_default:\s*)\S+",
        rf"\g<1>{value}",
        tail,
        count=1,
    )
    config_path.write_text(head + tail_new, encoding="utf-8")


def _set_work_max_retries(root: Path, value: str) -> None:
    config_path = root / ".onward.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    if "max_retries:" in text:
        text = re.sub(r"(?m)^(\s+max_retries:\s*)\S+", rf"\g<1>{value}", text)
    else:
        text = text.replace(
            "require_success_ack:",
            f"max_retries: {value}\n  require_success_ack:",
            1,
        )
    config_path.write_text(text, encoding="utf-8")


def _set_task_run_count(path: Path, n: int) -> None:
    text = path.read_text(encoding="utf-8")
    if re.search(r"(?m)^run_count:\s*\d+\s*$", text):
        text = re.sub(r"(?m)^run_count:\s*\d+\s*$", f"run_count: {n}", text)
    else:
        text = text.replace("status:", f"run_count: {n}\nstatus:", 1)
    path.write_text(text, encoding="utf-8")


def _set_executor_block_enabled(root: Path, value: str) -> None:
    config_path = root / ".onward.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    pos = text.find("executor:")
    assert pos >= 0
    head, tail = text[:pos], text[pos:]
    tail_new = re.sub(r"(?m)^(\s+enabled:\s*)\S+", rf"\g<1>{value}", tail, count=1)
    config_path.write_text(head + tail_new, encoding="utf-8")


def test_work_task_fails_when_executor_disabled(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    _set_executor_block_enabled(tmp_path, "false")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "failed" in out

    task_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-001-ship.md").read_text(encoding="utf-8")
    assert 'status: "failed"' in task_raw


def test_work_chunk_sequential_false_stops_after_one_task(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    _set_sequential_by_default(tmp_path, "false")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "One"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Two"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.count("Run RUN-") == 1
    assert "sequential_by_default is false" in out

    chunk_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/chunks/CHUNK-001-build.md").read_text(encoding="utf-8")
    assert 'status: "in_progress"' in chunk_raw

    one = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-001-one.md").read_text(encoding="utf-8")
    two = (tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-002-two.md").read_text(encoding="utf-8")
    assert 'status: "completed"' in one
    assert 'status: "open"' in two


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


def test_work_chunk_fails_when_pre_chunk_shell_hook_fails(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    _set_hook_value(tmp_path, "pre_chunk_shell", '  pre_chunk_shell:\n    - "exit 7"')
    _set_hook_value(tmp_path, "post_task_markdown", "  post_task_markdown: null")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "pre_chunk_shell" in out


def test_work_chunk_runs_pre_chunk_shell_hook(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    _set_hook_value(tmp_path, "pre_chunk_shell", '  pre_chunk_shell:\n    - "echo ok > .onward/pre-chunk.txt"')
    _set_hook_value(tmp_path, "post_task_markdown", "  post_task_markdown: null")
    _set_hook_value(tmp_path, "post_chunk_markdown", "  post_chunk_markdown: null")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "CHUNK-001"])
    capsys.readouterr()
    assert code == 0
    assert (tmp_path / ".onward/pre-chunk.txt").exists()


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
    assert 'status: "failed"' in task_raw


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
    assert "Run history:" in out
    assert "RUN-" in out
    assert "completed" in out
    assert "log:" in out


def test_show_task_without_runs_shows_empty_history(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    assert cli.main(["show", "--root", str(tmp_path), "TASK-001"]) == 0
    out = capsys.readouterr().out
    assert "Run history:" in out
    assert "(no runs recorded)" in out



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
    assert payload.get("schema_version") == 1
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


def test_work_plan_drains_all_chunks_and_completes_plan(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "One"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "A1"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "A2"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Two"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-002", "B1"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-002", "B2"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Plan PLAN-001 completed" in out
    assert "(2 chunks," in out
    plan_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/plan.md").read_text(encoding="utf-8")
    assert 'status: "completed"' in plan_raw


def test_work_plan_stops_after_chunk_task_failure(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "false")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "One"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Fail"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Two"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-002", "Later"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Stopping plan work" in out
    plan_raw = (tmp_path / ".onward/plans/PLAN-001-alpha/plan.md").read_text(encoding="utf-8")
    assert 'status: "in_progress"' in plan_raw
    chunk2 = next((tmp_path / ".onward/plans/PLAN-001-alpha/chunks").glob("CHUNK-002-*.md"))
    assert 'status: "open"' in chunk2.read_text(encoding="utf-8")


def test_work_plan_skips_completed_chunks(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "One"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Only"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Two"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-002", "Later"]) == 0
    capsys.readouterr()

    assert cli.main(["work", "--root", str(tmp_path), "CHUNK-001"]) == 0
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.count("Run RUN-") == 1


def test_work_plan_already_completed(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    plan_path = next((tmp_path / ".onward/plans").glob("PLAN-001-*/plan.md"))
    text = plan_path.read_text(encoding="utf-8")
    plan_path.write_text(text.replace('status: "open"', 'status: "completed"'), encoding="utf-8")
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "already completed" in out


def test_work_rejects_non_task_chunk_plan(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    note = tmp_path / ".onward/plans/NOTE-001-test.md"
    note.write_text(
        '---\n'
        'id: "NOTE-001"\n'
        'type: "note"\n'
        'title: "n"\n'
        'status: "open"\n'
        'created_at: "2026-01-01T00:00:00Z"\n'
        'updated_at: "2026-01-01T00:00:00Z"\n'
        "---\n\n",
        encoding="utf-8",
    )
    capsys.readouterr()

    code = cli.main(["work", "--root", str(tmp_path), "NOTE-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "task, chunk, or plan" in out


def test_post_task_shell_receives_onward_env_vars(tmp_path: Path, capsys, monkeypatch):
    """Default post_task_shell sees ONWARD_* (cleared in _init_workspace; re-enable for this test)."""
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    _set_executor(tmp_path, "true")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    captured: list[dict[str, str]] = []
    orig_run = subprocess.run

    def fake_run(*args, **kwargs):
        env = kwargs.get("env")
        if kwargs.get("shell") and isinstance(env, dict) and env.get("ONWARD_TASK_ID"):
            captured.append(
                {
                    "ONWARD_RUN_ID": env.get("ONWARD_RUN_ID", ""),
                    "ONWARD_TASK_ID": env.get("ONWARD_TASK_ID", ""),
                    "ONWARD_TASK_TITLE": env.get("ONWARD_TASK_TITLE", ""),
                }
            )
            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()
        return orig_run(*args, **kwargs)

    with patch("onward.execution.subprocess.run", fake_run):
        assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0

    assert len(captured) == 1
    post = captured[0]
    assert post["ONWARD_TASK_ID"] == "TASK-001"
    assert "Ship" in post["ONWARD_TASK_TITLE"]
    assert post["ONWARD_RUN_ID"].startswith("RUN-")
