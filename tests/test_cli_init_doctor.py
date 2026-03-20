from pathlib import Path

from onward import cli


def test_init_creates_expected_layout(tmp_path: Path, capsys):
    exit_code = cli.main(["init", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Initialized Onward workspace" in out

    assert (tmp_path / ".onward.config.yaml").exists()
    assert (tmp_path / ".onward/plans/index.yaml").exists()
    assert (tmp_path / ".onward/plans/recent.yaml").exists()
    assert (tmp_path / ".onward/templates/plan.md").exists()
    assert (tmp_path / ".onward/prompts/split-plan.md").exists()
    assert (tmp_path / ".onward/prompts/split-chunk.md").exists()
    assert (tmp_path / ".onward/ongoing.json").exists()

    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".onward/plans/.archive/" in gitignore
    assert ".onward/sync/" in gitignore
    assert ".onward/runs/" in gitignore
    assert ".onward/ongoing.json" in gitignore
    assert ".dogfood/" in gitignore

    config = (tmp_path / ".onward.config.yaml").read_text(encoding="utf-8")
    assert "# Onward workspace config." in config
    assert "# Schema version for future migrations." in config
    assert "# Executor command to run for `onward work` task execution." in config
    assert "# Default model used by `onward split` decomposition (blank = use default)." in config


def test_doctor_passes_after_init(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Doctor check passed" in out


def test_doctor_fails_on_invalid_ongoing_json(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    (tmp_path / ".onward/ongoing.json").write_text("{not json", encoding="utf-8")

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "invalid json in .onward/ongoing.json" in out


def test_doctor_detects_duplicate_ids(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    capsys.readouterr()

    plan_file = tmp_path / ".onward/plans/PLAN-001-alpha/plan.md"
    duplicate = tmp_path / ".onward/plans/PLAN-001-alpha/chunks/CHUNK-999-dup.md"
    duplicate.write_text(plan_file.read_text(encoding="utf-8"), encoding="utf-8")

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "duplicate id found: PLAN-001" in out
