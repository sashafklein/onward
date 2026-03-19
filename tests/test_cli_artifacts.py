from pathlib import Path

from trains import cli


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def test_new_plan_chunk_task_list_and_show(tmp_path: Path, capsys):
    _init_workspace(tmp_path)

    assert (
        cli.main(
            [
                "new",
                "--root",
                str(tmp_path),
                "plan",
                "Implement Runtime",
                "--description",
                "core runtime",
            ]
        )
        == 0
    )
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Execution Loop"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Persist Run State"]) == 0
    capsys.readouterr()

    list_code = cli.main(["list", "--root", str(tmp_path)])
    list_out = capsys.readouterr().out
    assert list_code == 0
    assert "PLAN-001" in list_out
    assert "CHUNK-001" in list_out
    assert "TASK-001" in list_out

    show_code = cli.main(["show", "--root", str(tmp_path), "TASK-001"])
    show_out = capsys.readouterr().out
    assert show_code == 0
    assert "# TASK-001 Persist Run State" in show_out
    assert 'depends_on: []' in show_out
    assert 'acceptance: []' in show_out


def test_new_ids_increment(tmp_path: Path, capsys):
    _init_workspace(tmp_path)

    assert cli.main(["new", "--root", str(tmp_path), "plan", "One"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Two"]) == 0
    capsys.readouterr()

    out = (tmp_path / ".train/plans/index.yaml").read_text(encoding="utf-8")
    assert 'id: "PLAN-001"' in out
    assert 'id: "PLAN-002"' in out


def test_new_chunk_fails_when_plan_missing(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    capsys.readouterr()

    code = cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-999", "Ghost Chunk"])
    out = capsys.readouterr().out

    assert code == 1
    assert "Error: plan not found: PLAN-999" in out


def test_new_task_fails_when_chunk_missing(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    capsys.readouterr()

    code = cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-999", "Ghost Task"])
    out = capsys.readouterr().out

    assert code == 1
    assert "Error: chunk not found: CHUNK-999" in out


def test_show_missing_id_returns_nonzero(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    capsys.readouterr()

    code = cli.main(["show", "--root", str(tmp_path), "TASK-404"])
    out = capsys.readouterr().out

    assert code == 1
    assert "Artifact not found: TASK-404" in out


def test_status_transitions_progress_and_recent(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Implement"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--root", str(tmp_path), "TASK-001"]) == 0
    progress_code = cli.main(["progress", "--root", str(tmp_path)])
    progress_out = capsys.readouterr().out

    assert progress_code == 0
    assert "TASK-001" in progress_out
    assert "in_progress" in progress_out

    assert cli.main(["complete", "--root", str(tmp_path), "TASK-001"]) == 0
    recent_code = cli.main(["recent", "--root", str(tmp_path), "--limit", "5"])
    recent_out = capsys.readouterr().out

    assert recent_code == 0
    assert "TASK-001" in recent_out
    assert "\tcompleted\t" in recent_out


def test_archive_moves_plan_out_of_active_set(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Archive Me"]) == 0
    capsys.readouterr()

    archive_code = cli.main(["archive", "--root", str(tmp_path), "PLAN-001"])
    archive_out = capsys.readouterr().out

    assert archive_code == 0
    assert "Archived PLAN-001" in archive_out
    assert (tmp_path / ".train/plans/.archive/PLAN-001-archive-me/plan.md").exists()

    list_code = cli.main(["list", "--root", str(tmp_path), "--type", "plan"])
    list_out = capsys.readouterr().out
    assert list_code == 0
    assert "No artifacts found" in list_out


def test_next_prefers_ready_tasks_in_in_progress_chunk(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Task One"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Task Two"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--root", str(tmp_path), "CHUNK-001"]) == 0
    capsys.readouterr()

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("TASK-001\ttask\topen\t")


def test_next_skips_task_with_unmet_dependencies(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Deps"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Prereq"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Blocked"]) == 0
    capsys.readouterr()

    blocked_task_path = tmp_path / ".train/plans/PLAN-001-deps/tasks/TASK-002-blocked.md"
    raw = blocked_task_path.read_text(encoding="utf-8")
    raw = raw.replace("depends_on: []", "depends_on:\n  - TASK-001")
    blocked_task_path.write_text(raw, encoding="utf-8")

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("TASK-001\ttask\topen\t")
