"""Run snapshot files under `.onward/runs/RUN-*.json` must be valid JSON; legacy YAML-shaped files still parse."""

import json
from pathlib import Path

from onward.util import _dump_run_json_record, _read_run_json_record


def test_dump_run_record_is_valid_json_round_trip():
    rec = {
        "id": "RUN-2026-03-20T12-00-00Z-TASK-001",
        "type": "run",
        "target": "TASK-001",
        "plan": "PLAN-001",
        "chunk": "CHUNK-001",
        "status": "completed",
        "model": "claude-sonnet-4-6",
        "executor": "ralph",
        "started_at": "2026-03-20T12:00:00Z",
        "finished_at": "2026-03-20T12:01:00Z",
        "log_path": ".onward/runs/RUN-2026-03-20T12-00-00Z-TASK-001.log",
        "error": "",
    }
    text = _dump_run_json_record(rec)
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
executor: "ralph"
started_at: "2026-01-01T00:00:00Z"
finished_at: "2026-01-01T00:01:00Z"
log_path: ".onward/runs/x.log"
error: "oops"
"""
    parsed = _read_run_json_record(legacy)
    assert parsed["id"] == "RUN-old-TASK-001"
    assert parsed["status"] == "failed"
    assert parsed["error"] == "oops"


def test_new_writes_are_json_files(tmp_path: Path, capsys):
    from onward import cli

    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    config_path = tmp_path / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    config_path.write_text(raw.replace("  command: ralph", '  command: "true"'), encoding="utf-8")
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()
    assert cli.main(["work", "--root", str(tmp_path), "TASK-001"]) == 0

    run_file = next((tmp_path / ".onward/runs").glob("RUN-*-TASK-001.json"))
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
executor: "ralph"
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
    assert "status: completed" in out
