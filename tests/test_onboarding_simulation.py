"""Fresh-workspace onboarding path (init → doctor → artifacts → next/report → work).

CI-runnable counterpart to INSTALLATION / CONTRIBUTION quickstart and dogfood e2e (PLAN-010 TASK-014).
Executor is set to ``true`` so no external ralph binary is required.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from onward import cli


def _set_executor(root: Path, command: str) -> None:
    config_path = root / ".onward.config.yaml"
    raw = config_path.read_text(encoding="utf-8")
    raw = raw.replace("  command: ralph", f'  command: "{command}"')
    config_path.write_text(raw, encoding="utf-8")


def test_onboarding_flow_init_doctor_new_next_report_work(tmp_path: Path, capsys) -> None:
    root = str(tmp_path)

    assert cli.main(["init", "--root", root]) == 0
    assert cli.main(["doctor", "--root", root]) == 0
    doctor_out = capsys.readouterr().out
    assert "Doctor check passed" in doctor_out

    assert cli.main(["new", "--root", root, "plan", "Onboarding Sim"]) == 0
    assert cli.main(["new", "--root", root, "chunk", "PLAN-001", "First chunk"]) == 0
    assert cli.main(["new", "--root", root, "task", "CHUNK-001", "First task"]) == 0
    capsys.readouterr()

    assert cli.main(["next", "--root", root]) == 0
    next_out = capsys.readouterr().out
    assert "TASK-001" in next_out

    assert cli.main(["report", "--root", root]) == 0
    capsys.readouterr()

    _set_executor(tmp_path, "true")
    capsys.readouterr()
    assert cli.main(["work", "--root", root, "TASK-001"]) == 0
    work_out = capsys.readouterr().out
    assert "Run RUN-" in work_out

    task_paths = list(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    assert len(task_paths) == 1
    assert 'status: "completed"' in task_paths[0].read_text(encoding="utf-8")

    run_files = list((tmp_path / ".onward/runs").glob("RUN-*-TASK-001.json"))
    assert len(run_files) == 1
    assert json.loads(run_files[0].read_text(encoding="utf-8"))["status"] == "completed"

    index_raw = (tmp_path / ".onward/plans/index.yaml").read_text(encoding="utf-8")
    # Index uses YAML list-of-maps; simple parser cannot load it — assert structurally.
    assert re.search(
        r'id:\s*"TASK-001"[\s\S]*?status:\s*"completed"',
        index_raw,
    ), "index.yaml should list TASK-001 as completed after work"

    assert cli.main(["report", "--root", root]) == 0
