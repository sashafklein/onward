from pathlib import Path

from onward import cli
from onward.artifacts import find_by_id

from tests.workspace_helpers import set_artifact_status_in_frontmatter


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def _create_plan_and_task(root: Path) -> None:
    assert cli.main(["new", "--root", str(root), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(root), "chunk", "PLAN-001", "Backend"]) == 0
    assert cli.main(["new", "--root", str(root), "task", "CHUNK-001", "Add schema"]) == 0


def test_note_add_creates_file(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)
    capsys.readouterr()

    code = cli.main(["note", "--root", str(tmp_path), "TASK-001", "todo: check edge case"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Note added to TASK-001" in out

    notes_path = tmp_path / ".onward/notes/TASK-001.md"
    assert notes_path.exists()
    content = notes_path.read_text(encoding="utf-8")
    assert "todo: check edge case" in content
    assert "## 20" in content  # timestamp header


def test_note_view_shows_notes(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)

    cli.main(["note", "--root", str(tmp_path), "TASK-001", "first note"])
    cli.main(["note", "--root", str(tmp_path), "TASK-001", "second note"])
    capsys.readouterr()

    code = cli.main(["note", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out

    assert code == 0
    assert "first note" in out
    assert "second note" in out
    assert "Notes for TASK-001" in out


def test_note_view_empty(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)
    capsys.readouterr()

    code = cli.main(["note", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out

    assert code == 0
    assert "No notes for TASK-001" in out


def test_note_sets_has_notes_frontmatter(tmp_path: Path):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)

    artifact_before = find_by_id(tmp_path, "TASK-001")
    assert not artifact_before.metadata.get("has_notes")

    cli.main(["note", "--root", str(tmp_path), "TASK-001", "a note"])

    artifact_after = find_by_id(tmp_path, "TASK-001")
    assert artifact_after.metadata.get("has_notes") is True


def test_note_on_plan(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)
    capsys.readouterr()

    code = cli.main(["note", "--root", str(tmp_path), "PLAN-001", "plan-level thought"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Note added to PLAN-001" in out

    notes_path = tmp_path / ".onward/notes/PLAN-001.md"
    assert notes_path.exists()
    assert "plan-level thought" in notes_path.read_text(encoding="utf-8")


def test_note_on_chunk(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)
    capsys.readouterr()

    code = cli.main(["note", "--root", str(tmp_path), "CHUNK-001", "chunk observation"])
    assert code == 0

    notes_path = tmp_path / ".onward/notes/CHUNK-001.md"
    assert notes_path.exists()


def test_complete_shows_notes(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)

    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    set_artifact_status_in_frontmatter(task_path, "in_progress")
    cli.main(["note", "--root", str(tmp_path), "TASK-001", "remember to update docs"])
    capsys.readouterr()

    code = cli.main(["complete", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Related notes for TASK-001" in out
    assert "remember to update docs" in out


def test_cancel_shows_notes(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)

    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    set_artifact_status_in_frontmatter(task_path, "in_progress")
    cli.main(["note", "--root", str(tmp_path), "TASK-001", "this approach won't work"])
    capsys.readouterr()

    code = cli.main(["cancel", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Related notes for TASK-001" in out
    assert "this approach won't work" in out


def test_complete_no_notes_no_section(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)

    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    set_artifact_status_in_frontmatter(task_path, "in_progress")
    capsys.readouterr()

    code = cli.main(["complete", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Related notes" not in out


def test_progress_does_not_emit_related_notes_section(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)

    cli.main(["note", "--root", str(tmp_path), "TASK-001", "a note exists"])
    capsys.readouterr()
    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    set_artifact_status_in_frontmatter(task_path, "in_progress")
    capsys.readouterr()

    code = cli.main(["progress", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert code == 0
    assert "Related notes" not in out


def test_note_appends_multiple(tmp_path: Path):
    _init_workspace(tmp_path)
    _create_plan_and_task(tmp_path)

    cli.main(["note", "--root", str(tmp_path), "TASK-001", "note one"])
    cli.main(["note", "--root", str(tmp_path), "TASK-001", "note two"])
    cli.main(["note", "--root", str(tmp_path), "TASK-001", "note three"])

    content = (tmp_path / ".onward/notes/TASK-001.md").read_text(encoding="utf-8")
    assert content.count("## 20") == 3
    assert "note one" in content
    assert "note two" in content
    assert "note three" in content


def test_note_missing_artifact_errors(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    capsys.readouterr()

    code = cli.main(["note", "--root", str(tmp_path), "TASK-999", "a note"])
    out = capsys.readouterr().out

    assert code == 1
    assert "not found" in out
