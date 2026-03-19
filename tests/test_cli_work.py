from pathlib import Path

from onward import cli


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def _set_executor(root: Path, command: str) -> None:
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    raw = raw.replace("  command: ralph", f"  command: {command}")
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
