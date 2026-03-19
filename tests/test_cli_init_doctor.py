from pathlib import Path

from trains import cli


def test_init_creates_expected_layout(tmp_path: Path, capsys):
    exit_code = cli.main(["init", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Initialized Trains workspace" in out

    assert (tmp_path / ".train.config.yaml").exists()
    assert (tmp_path / ".train/plans/index.yaml").exists()
    assert (tmp_path / ".train/plans/recent.yaml").exists()
    assert (tmp_path / ".train/templates/plan.md").exists()
    assert (tmp_path / ".train/ongoing.json").exists()

    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".train/plans/.archive/" in gitignore
    assert ".train/runs/" in gitignore
    assert ".train/ongoing.json" in gitignore
    assert ".dogfood/" in gitignore


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

    (tmp_path / ".train/ongoing.json").write_text("{not json", encoding="utf-8")

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "invalid json in .train/ongoing.json" in out


def test_doctor_detects_duplicate_ids(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    capsys.readouterr()

    plan_file = tmp_path / ".train/plans/PLAN-001-alpha/plan.md"
    duplicate = tmp_path / ".train/plans/PLAN-001-alpha/chunks/CHUNK-999-dup.md"
    duplicate.write_text(plan_file.read_text(encoding="utf-8"), encoding="utf-8")

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "duplicate id found: PLAN-001" in out
