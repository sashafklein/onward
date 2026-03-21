from pathlib import Path

from onward import cli

from tests.workspace_helpers import set_artifact_status_in_frontmatter


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def _null_post_chunk_hook(root: Path) -> None:
    """Avoid executor-backed post_chunk hook in tests (finalize_chunks_all_tasks_terminal)."""
    p = root / ".onward.config.yaml"
    raw = p.read_text(encoding="utf-8")
    raw = raw.replace(
        "post_chunk_markdown: .onward/hooks/post-chunk.md",
        "post_chunk_markdown: null",
    )
    p.write_text(raw, encoding="utf-8")


def test_new_task_file_has_no_blocked_by_key(tmp_path: Path):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "T"]) == 0
    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    assert "blocked_by" not in task_path.read_text(encoding="utf-8")


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

    out = (tmp_path / ".onward/plans/index.yaml").read_text(encoding="utf-8")
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

    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    set_artifact_status_in_frontmatter(task_path, "in_progress")
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
    assert (tmp_path / ".onward/plans/.archive/PLAN-001-archive-me/plan.md").exists()

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

    chunk_path = next(tmp_path.glob(".onward/plans/**/chunks/CHUNK-001-*.md"))
    set_artifact_status_in_frontmatter(chunk_path, "in_progress")
    capsys.readouterr()

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("TASK-001\ttask\topen\t")


def test_next_skips_until_blocked_by_prereq_completes_like_depends_on(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "First"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Second"]) == 0
    capsys.readouterr()

    task_two = next(tmp_path.glob(".onward/plans/**/tasks/TASK-002-*.md"))
    raw = task_two.read_text(encoding="utf-8")
    task_two.write_text(
        raw.replace("depends_on: []", "depends_on: []\nblocked_by:\n  - TASK-001"),
        encoding="utf-8",
    )

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("TASK-001\ttask\topen\t")

    assert cli.main(["complete", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("TASK-002\ttask\topen\t")


def test_next_skips_task_with_unmet_dependencies(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Deps"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Prereq"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Blocked"]) == 0
    capsys.readouterr()

    blocked_task_path = tmp_path / ".onward/plans/PLAN-001-deps/tasks/TASK-002-blocked.md"
    raw = blocked_task_path.read_text(encoding="utf-8")
    raw = raw.replace("depends_on: []", "depends_on:\n  - TASK-001")
    blocked_task_path.write_text(raw, encoding="utf-8")

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("TASK-001\ttask\topen\t")


def test_next_includes_in_progress_task(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Task One"]) == 0
    capsys.readouterr()

    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    set_artifact_status_in_frontmatter(task_path, "in_progress")
    capsys.readouterr()

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("TASK-001\ttask\tin_progress\t")


def test_next_skips_open_chunk_when_only_human_tasks_remain(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Human only"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert (
        cli.main(
            ["new", "--root", str(tmp_path), "task", "CHUNK-001", "Human step", "--human"]
        )
        == 0
    )
    capsys.readouterr()

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("PLAN-001\tplan\topen\t")


def test_complete_last_task_finalizes_chunk(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _null_post_chunk_hook(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Finalize"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Only task"]) == 0
    capsys.readouterr()

    assert cli.main(["complete", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    chunk_path = next(tmp_path.glob(".onward/plans/**/chunks/CHUNK-001-*.md"))
    assert 'status: "completed"' in chunk_path.read_text(encoding="utf-8")

    code = cli.main(["next", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("PLAN-001\tplan\topen\t")


def test_list_filters_project_human_and_blocking(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Proj", "--project", "alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Chunk", "--project", "alpha"]) == 0
    assert (
        cli.main(
            [
                "new",
                "--root",
                str(tmp_path),
                "task",
                "CHUNK-001",
                "Human blocker",
                "--project",
                "alpha",
                "--human",
            ]
        )
        == 0
    )
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Blocked task", "--project", "alpha"]) == 0
    capsys.readouterr()

    blocked_task_path = tmp_path / ".onward/plans/PLAN-001-proj/tasks/TASK-002-blocked-task.md"
    raw = blocked_task_path.read_text(encoding="utf-8")
    raw = raw.replace("depends_on: []", "depends_on:\n  - TASK-001")
    blocked_task_path.write_text(raw, encoding="utf-8")

    project_code = cli.main(["list", "--root", str(tmp_path), "--project", "alpha"])
    project_out = capsys.readouterr().out
    assert project_code == 0
    assert "project=alpha" in project_out

    human_blocking_code = cli.main(["list", "--root", str(tmp_path), "--blocking", "--human"])
    human_blocking_out = capsys.readouterr().out
    assert human_blocking_code == 0
    assert "TASK-001" in human_blocking_out
    assert "human=true" in human_blocking_out
    assert "TASK-002" not in human_blocking_out


def test_report_contains_expected_sections(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Report Plan", "--project", "alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build", "--project", "alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Human blocker", "--project", "alpha", "--human"]) == 0
    chunk_path = next(tmp_path.glob(".onward/plans/**/chunks/CHUNK-001-*.md"))
    set_artifact_status_in_frontmatter(chunk_path, "in_progress")
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path), "--project", "alpha", "--no-color"])
    out = capsys.readouterr().out
    assert code == 0
    assert "== Onward Report ==" in out
    assert "[In Progress]" in out
    assert "[Upcoming]" in out
    assert "[Next]" in out
    assert "[Blocking Human Tasks]" in out
    assert "[Recent Completed]" in out
    assert "[Active work tree]" in out


def test_tree_outputs_open_hierarchy(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Tree Plan", "--project", "alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Tree Chunk", "--project", "alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Human task", "--project", "alpha", "--human"]) == 0
    capsys.readouterr()

    code = cli.main(["tree", "--root", str(tmp_path), "--project", "alpha", "--no-color"])
    out = capsys.readouterr().out
    assert code == 0
    assert "PLAN-001 [open] Tree Plan" in out
    assert "CHUNK-001 [open] Tree Chunk" in out
    assert "TASK-001 [open] (H) Human task" in out


def test_tree_hides_completed_tasks_and_chunks(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _null_post_chunk_hook(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Plan"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Chunk"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Done"]) == 0
    assert cli.main(["complete", "--root", str(tmp_path), "TASK-001"]) == 0
    capsys.readouterr()

    code = cli.main(["tree", "--root", str(tmp_path), "--no-color"])
    out = capsys.readouterr().out
    assert code == 0
    assert "PLAN-001" not in out, "plan with no active children should be excluded"
    assert "TASK-001" not in out
    assert "CHUNK-001" not in out
