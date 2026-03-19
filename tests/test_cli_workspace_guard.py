from pathlib import Path

from onward import cli


def test_non_init_command_fails_outside_workspace(tmp_path: Path, capsys):
    code = cli.main(["list", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 1
    assert "not an Onward workspace" in out
    assert "onward init" in out


def test_init_still_works_outside_workspace(tmp_path: Path, capsys):
    code = cli.main(["init", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "Initialized Onward workspace" in out


def test_other_commands_work_after_init(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    code = cli.main(["list", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "No artifacts found" in out
