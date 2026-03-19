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
