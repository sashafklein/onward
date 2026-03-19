from pathlib import Path

from trains import cli


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def test_split_plan_dry_run_does_not_write_files(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Decompose Me"]) == 0
    capsys.readouterr()

    code = cli.main(["split", "--root", str(tmp_path), "PLAN-001", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Split dry-run for PLAN-001" in out
    assert "PLAN: create CHUNK-" in out

    chunk_files = list((tmp_path / ".train/plans/PLAN-001-decompose-me/chunks").glob("*.md"))
    assert chunk_files == []


def test_split_chunk_creates_task_with_acceptance(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build API"]) == 0
    capsys.readouterr()

    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        '{"tasks":[{"title":"Add endpoint","description":"Implement endpoint","acceptance":["returns 200"],"model":"gpt-5-mini","human":false}]}',
    )

    code = cli.main(["split", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Created TASK-001" in out

    task_path = tmp_path / ".train/plans/PLAN-001-alpha/tasks/TASK-001-add-endpoint.md"
    raw = task_path.read_text(encoding="utf-8")
    assert 'acceptance:\n  - "returns 200"' in raw
    assert 'model: "gpt-5-mini"' in raw


def test_split_validation_error_writes_nothing(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Bad Split"]) == 0
    capsys.readouterr()

    monkeypatch.setenv("TRAIN_SPLIT_RESPONSE", '{"chunks":[{"title":"Missing description"}]}')
    code = cli.main(["split", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "split validation failed: chunks[1].description is required" in out

    chunk_files = list((tmp_path / ".train/plans/PLAN-001-bad-split/chunks").glob("*.md"))
    assert chunk_files == []
