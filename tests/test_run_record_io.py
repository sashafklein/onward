"""Run snapshot files under `.onward/runs/RUN-*.json` must be valid JSON; legacy YAML-shaped files still parse."""

import json
from pathlib import Path

from onward.executor import ExecutorResult
from onward.util import dump_run_json_record, read_run_json_record

from tests.conftest import make_default_layout
from tests.workspace_helpers import (
    clear_post_chunk_markdown,
    clear_post_task_markdown,
    clear_post_task_shell,
)


def test_dump_run_record_is_valid_json_round_trip():
    rec = {
        "id": "RUN-2026-03-20T12-00-00Z-TASK-001",
        "type": "run",
        "target": "TASK-001",
        "plan": "PLAN-001",
        "chunk": "CHUNK-001",
        "status": "completed",
        "model": "claude-sonnet-4-6",
        "executor": "true",
        "started_at": "2026-03-20T12:00:00Z",
        "finished_at": "2026-03-20T12:01:00Z",
        "log_path": ".onward/runs/RUN-2026-03-20T12-00-00Z-TASK-001.log",
        "error": "",
    }
    text = dump_run_json_record(rec)
    parsed = json.loads(text)
    assert parsed == rec
    assert text.strip().startswith("{")
    assert "\n" in text


def test_read_run_record_accepts_legacy_simple_yaml_shape():
    legacy = """id: "RUN-old-TASK-001"
type: "run"
target: "TASK-001"
status: "failed"
model: "opus"
executor: "true"
started_at: "2026-01-01T00:00:00Z"
finished_at: "2026-01-01T00:01:00Z"
log_path: ".onward/runs/x.log"
error: "oops"
"""
    parsed = read_run_json_record(legacy)
    assert parsed["id"] == "RUN-old-TASK-001"
    assert parsed["status"] == "failed"
    assert parsed["error"] == "oops"


def test_read_run_record_fills_optional_defaults_for_sparse_legacy():
    sparse = """id: "RUN-sparse-TASK-001"
target: "TASK-001"
status: "completed"
model: "opus"
started_at: "2026-01-01T00:00:00Z"
log_path: ".onward/runs/x.log"
"""
    parsed = read_run_json_record(sparse)
    assert parsed["type"] == "run"
    assert parsed["plan"] is None
    assert parsed["chunk"] is None
    assert parsed["executor"] == "onward-exec"
    assert parsed["error"] == ""
    assert parsed["finished_at"] is None


def test_new_writes_are_json_files(tmp_path: Path, capsys):
    from onward import cli

    from tests.workspace_helpers import clear_post_task_shell

    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    clear_post_task_shell(tmp_path)
    config_path = tmp_path / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    config_path.write_text(raw.replace("  command: builtin", '  command: "true"'), encoding="utf-8")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()
    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0

    run_file = next((tmp_path / ".onward/runs/TASK-001").glob("info-*.json"))
    body = run_file.read_text(encoding="utf-8")
    json.loads(body)
    assert body.lstrip().startswith("{")


def test_show_reads_legacy_yaml_shaped_run_file(tmp_path: Path, capsys):
    from onward import cli

    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0

    runs = tmp_path / ".onward/runs"
    runs.mkdir(parents=True, exist_ok=True)
    legacy = """id: "RUN-legacy-TASK-001"
type: "run"
target: "TASK-001"
status: "completed"
model: "opus"
executor: "true"
started_at: "2026-01-01T00:00:00Z"
finished_at: "2026-01-01T00:01:00Z"
log_path: ".onward/runs/x.log"
error: ""
"""
    (runs / "RUN-legacy-TASK-001.json").write_text(legacy, encoding="utf-8")
    capsys.readouterr()

    assert cli.main(["show", "--root", str(tmp_path), "TASK-001"]) == 0
    out = capsys.readouterr().out
    assert "RUN-legacy-TASK-001" in out
    assert "completed" in out


def _set_builtin_executor(root: Path) -> None:
    """Scaffold already defaults to builtin — this is a no-op kept for clarity."""
    pass


def _prepare_task_for_tier_low_model(task_path: Path) -> None:
    """Drop explicit ``model`` (``onward new task`` defaults to sonnet-4-6) and set tier effort."""
    lines = task_path.read_text(encoding="utf-8").splitlines()
    filtered = [ln for ln in lines if not ln.lstrip().startswith("model:")]
    text = "\n".join(filtered)
    if 'effort: "low"' not in text:
        text = text.replace('type: "task"\n', 'type: "task"\neffort: "low"\n', 1)
    task_path.write_text(text.rstrip() + "\n", encoding="utf-8")


def test_run_record_builtin_executor_and_tier_resolved_model(tmp_path: Path, monkeypatch, capsys):
    """Run JSON stores executor label and tier-resolved model (not raw task metadata)."""
    from onward import cli

    class _RecordingExecutor:
        def __init__(self) -> None:
            self.active_snapshots: list[list[dict]] = []

        def execute_task(self, root: Path, ctx):  # noqa: ANN001
            from onward.execution import load_ongoing

            layout = make_default_layout(root)
            ongoing = load_ongoing(layout)
            self.active_snapshots.append(list(ongoing.get("active_runs", [])))
            return ExecutorResult(
                task_id=str(ctx.task.metadata.get("id", "")),
                run_id=ctx.run_id,
                success=True,
                output="executor stdout line",
                error="",
                ack=None,
                return_code=0,
            )

        def execute_batch(self, root: Path, tasks):  # noqa: ANN001
            for ctx in tasks:
                yield self.execute_task(root, ctx)

    recorder = _RecordingExecutor()
    monkeypatch.setattr("onward.execution.resolve_executor", lambda _cfg: recorder)

    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    clear_post_task_shell(tmp_path)
    clear_post_task_markdown(tmp_path)
    clear_post_chunk_markdown(tmp_path)
    _set_builtin_executor(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    _prepare_task_for_tier_low_model(task_path)
    capsys.readouterr()

    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0

    run_file = next((tmp_path / ".onward/runs/TASK-001").glob("info-*.json"))
    rec = json.loads(run_file.read_text(encoding="utf-8"))
    assert rec["executor"] == "builtin"
    assert rec["model"] == "haiku-latest"
    assert rec["status"] == "completed"

    assert len(recorder.active_snapshots) == 1
    assert len(recorder.active_snapshots[0]) == 1
    assert recorder.active_snapshots[0][0]["target"] == "TASK-001"
    assert recorder.active_snapshots[0][0]["id"] == rec["id"]

    summary_name = run_file.name.replace("info-", "summary-").replace(".json", ".log")
    log_text = (run_file.parent / summary_name).read_text(encoding="utf-8")
    assert "$ builtin" in log_text
    assert "executor stdout line" in log_text

    ongoing = json.loads((tmp_path / ".onward/ongoing.json").read_text(encoding="utf-8"))
    assert ongoing.get("active_runs") == []
