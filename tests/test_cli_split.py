import json
import subprocess
from pathlib import Path

from onward import cli


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def test_split_plan_dry_run_does_not_write_files(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Decompose Me"]) == 0
    capsys.readouterr()

    code = cli.main(["split", "--root", str(tmp_path), "PLAN-001", "--dry-run", "--heuristic"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Split dry-run (plan→chunks) for PLAN-001" in out
    assert "CHUNK: create CHUNK-" in out

    chunk_files = list((tmp_path / ".onward/plans/PLAN-001-decompose-me/chunks").glob("*.md"))
    assert chunk_files == []


def test_split_chunk_dry_run_labels_tasks(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build API"]) == 0
    capsys.readouterr()

    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        '{"tasks":[{"title":"Add endpoint","description":"Implement","acceptance":["done"],"model":"gpt-5-mini","human":false}]}',
    )
    code = cli.main(["split", "--root", str(tmp_path), "CHUNK-001", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Split dry-run (chunk→tasks) for CHUNK-001" in out
    assert "TASK: create TASK-001" in out
    assert "PLAN: create" not in out
    assert "CHUNK: create" not in out

    task_files = list((tmp_path / ".onward/plans/PLAN-001-alpha/tasks").glob("*.md"))
    assert task_files == []


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

    task_path = tmp_path / ".onward/plans/PLAN-001-alpha/tasks/TASK-001-add-endpoint.md"
    raw = task_path.read_text(encoding="utf-8")
    assert "- returns 200" in raw
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

    chunk_files = list((tmp_path / ".onward/plans/PLAN-001-bad-split/chunks").glob("*.md"))
    assert chunk_files == []


def test_split_plan_creates_chunks(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Feature X"]) == 0
    capsys.readouterr()

    plan_path = tmp_path / ".onward/plans/PLAN-001-feature-x/plan.md"
    raw = plan_path.read_text(encoding="utf-8")
    raw = raw.replace("# Goals\n\n<!-- Bullets -->", "# Goals\n\n- Build the API\n- Build the UI")
    plan_path.write_text(raw, encoding="utf-8")

    code = cli.main(["split", "--root", str(tmp_path), "PLAN-001", "--heuristic"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Created CHUNK-001" in out
    assert "Created CHUNK-002" in out

    chunk_files = sorted((tmp_path / ".onward/plans/PLAN-001-feature-x/chunks").glob("*.md"))
    assert len(chunk_files) == 2

    chunk_raw = chunk_files[0].read_text(encoding="utf-8")
    assert 'type: "chunk"' in chunk_raw
    assert 'plan: "PLAN-001"' in chunk_raw
    assert 'status: "open"' in chunk_raw


def test_split_invalid_json_returns_error(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Bad JSON"]) == 0
    capsys.readouterr()

    monkeypatch.setenv("TRAIN_SPLIT_RESPONSE", "not valid json at all")
    code = cli.main(["split", "--root", str(tmp_path), "PLAN-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "invalid split JSON" in out


def test_split_rejects_non_splittable_type(tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "Ship"]) == 0
    capsys.readouterr()

    code = cli.main(["split", "--root", str(tmp_path), "TASK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "not splittable" in out


def test_split_collision_detection(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Existing"]) == 0
    capsys.readouterr()

    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        '{"tasks":[{"title":"First task","description":"Do thing","acceptance":["done"],"model":"gpt-5","human":false}]}',
    )
    code = cli.main(["split", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Created TASK-001" in out

    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        '{"tasks":[{"title":"Second task","description":"Do other thing","acceptance":["done"],"model":"gpt-5","human":false}]}',
    )
    code2 = cli.main(["split", "--root", str(tmp_path), "CHUNK-001"])
    out2 = capsys.readouterr().out
    assert code2 == 0
    assert "Created TASK-002" in out2


def test_split_deterministic_ids(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    capsys.readouterr()

    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        '{"tasks":['
        '{"title":"A","description":"First","acceptance":["done"],"model":"gpt-5","human":false},'
        '{"title":"B","description":"Second","acceptance":["done"],"model":"gpt-5","human":false},'
        '{"title":"C","description":"Third","acceptance":["done"],"model":"gpt-5","human":false}'
        "]}",
    )
    code = cli.main(["split", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Created TASK-001" in out
    assert "Created TASK-002" in out
    assert "Created TASK-003" in out

    task_files = sorted((tmp_path / ".onward/plans/PLAN-001-alpha/tasks").glob("TASK-*.md"))
    assert len(task_files) == 3
    assert "TASK-001" in task_files[0].name
    assert "TASK-002" in task_files[1].name
    assert "TASK-003" in task_files[2].name


def test_split_validation_duplicate_task_titles_dry_run(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    capsys.readouterr()
    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        '{"tasks":['
        '{"title":"Same","description":"a","acceptance":["x"],"model":"gpt-5","human":false},'
        '{"title":"Same","description":"b","acceptance":["y"],"model":"gpt-5","human":false}'
        "]}",
    )
    code = cli.main(["split", "--root", str(tmp_path), "CHUNK-001", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "duplicate task titles" in out


def test_split_validation_error_blocks_write(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    capsys.readouterr()
    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        '{"tasks":['
        '{"title":"Same","description":"a","acceptance":["x"],"model":"gpt-5","human":false},'
        '{"title":"Same","description":"b","acceptance":["y"],"model":"gpt-5","human":false}'
        "]}",
    )
    code = cli.main(["split", "--root", str(tmp_path), "CHUNK-001"])
    out = capsys.readouterr().out
    assert code == 1
    assert "duplicate task titles" in out
    task_files = list((tmp_path / ".onward/plans/PLAN-001-alpha/tasks").glob("*.md"))
    assert task_files == []


def test_split_force_writes_despite_validation_error(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    capsys.readouterr()
    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        '{"tasks":['
        '{"title":"Same","description":"a","acceptance":["x"],"model":"gpt-5","human":false},'
        '{"title":"Same","description":"b","acceptance":["y"],"model":"gpt-5","human":false}'
        "]}",
    )
    code = cli.main(["split", "--root", str(tmp_path), "CHUNK-001", "--force"])
    out = capsys.readouterr().out
    assert code == 0
    assert "ignored with --force" in out
    assert "Created TASK-" in out


def test_split_validation_task_dependency_cycle(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    capsys.readouterr()
    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        '{"tasks":['
        '{"title":"A","description":"a","acceptance":["x"],"model":"gpt-5","human":false,"depends_on_index":[1]},'
        '{"title":"B","description":"b","acceptance":["y"],"model":"gpt-5","human":false,"depends_on_index":[0]}'
        "]}",
    )
    code = cli.main(["split", "--root", str(tmp_path), "CHUNK-001", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "depends_on_index contains a cycle" in out


def test_split_validation_task_too_many_files_warns_and_errors(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    capsys.readouterr()
    files_7 = [f"src/f{i}.py" for i in range(7)]
    files_10 = [f"src/g{i}.py" for i in range(10)]
    import json

    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        json.dumps(
            {
                "tasks": [
                    {
                        "title": "Seven",
                        "description": "a",
                        "acceptance": ["x"],
                        "model": "gpt-5",
                        "human": False,
                        "files": files_7,
                    }
                ]
            }
        ),
    )
    code = cli.main(["split", "--root", str(tmp_path), "CHUNK-001", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "lists 7 files" in out

    monkeypatch.setenv(
        "TRAIN_SPLIT_RESPONSE",
        json.dumps(
            {
                "tasks": [
                    {
                        "title": "Ten",
                        "description": "a",
                        "acceptance": ["x"],
                        "model": "gpt-5",
                        "human": False,
                        "files": files_10,
                    }
                ]
            }
        ),
    )
    code2 = cli.main(["split", "--root", str(tmp_path), "CHUNK-001", "--dry-run"])
    out2 = capsys.readouterr().out
    assert code2 == 0
    assert "lists 10 files" in out2


def test_split_invokes_executor_with_split_payload(monkeypatch, tmp_path: Path, capsys):
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "AI Split"]) == 0
    capsys.readouterr()
    monkeypatch.delenv("TRAIN_SPLIT_RESPONSE", raising=False)
    monkeypatch.setattr("onward.split.preflight_executor_command", lambda _c: None)

    captured: dict[str, str | list[str]] = {}

    def fake_run(cmd, cwd=None, input=None, **kwargs):
        captured["cmd"] = list(cmd)
        captured["input"] = input
        return subprocess.CompletedProcess(
            cmd,
            0,
            '{"chunks":[{"title":"One","description":"Body","priority":"medium","model":"opus"}]}',
            "",
        )

    monkeypatch.setattr("onward.split.subprocess.run", fake_run)

    code = cli.main(["split", "--root", str(tmp_path), "PLAN-001", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Split dry-run" in out
    assert captured.get("input")
    payload = json.loads(str(captured["input"]))
    assert payload["type"] == "split"
    assert payload["split_type"] == "plan"
    assert payload["schema_version"] == 1
    assert "prompt" in payload
    assert "artifact_body" in payload
    assert payload["artifact_metadata"].get("id") == "PLAN-001"
