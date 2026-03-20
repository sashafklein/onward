import subprocess
from pathlib import Path

from onward import cli


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def _write_config_sync(main: Path, **sync_keys: str) -> None:
    path = main / ".onward.config.yaml"
    lines = [
        "version: 1",
        "",
        "sync:",
    ]
    for k, v in sync_keys.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def test_sync_status_local_mode(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert cli.main(["sync", "--root", str(tmp_path), "status"]) == 0
    out = capsys.readouterr().out
    assert "local" in out.lower()
    assert "n/a" in out.lower()


def test_sync_status_remote_not_initialized_branch_mode(tmp_path: Path, capsys):
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init")
    _git(main, "config", "user.email", "t@t")
    _git(main, "config", "user.name", "test")
    assert cli.main(["init", "--root", str(main)]) == 0
    _write_config_sync(main, mode="branch", branch="onward", repo="null", worktree_path=".onward/sync")
    _git(main, "add", "-A")
    _git(main, "commit", "-m", "init")
    capsys.readouterr()
    assert cli.main(["sync", "--root", str(main), "status"]) == 0
    out = capsys.readouterr().out
    assert "not initialized" in out


def test_sync_push_branch_with_origin(tmp_path: Path, capsys):
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)

    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init")
    _git(main, "config", "user.email", "t@t")
    _git(main, "config", "user.name", "test")
    assert cli.main(["init", "--root", str(main)]) == 0
    _write_config_sync(main, mode="branch", branch="onward", repo="null", worktree_path=".onward/sync")
    _git(main, "add", "-A")
    _git(main, "commit", "-m", "init")
    _git(main, "remote", "add", "origin", str(bare))
    _git(main, "push", "-u", "origin", "HEAD")

    assert cli.main(["new", "--root", str(main), "plan", "Alpha"]) == 0
    capsys.readouterr()
    assert cli.main(["sync", "--root", str(main), "push"]) == 0
    out = capsys.readouterr().out
    assert "Pushed to remote" in out
    assert (main / ".onward" / "sync" / ".git").exists()

    capsys.readouterr()
    assert cli.main(["sync", "--root", str(main), "status"]) == 0
    status_out = capsys.readouterr().out
    assert "clean" in status_out.lower()


def test_sync_repo_mode_push_and_pull(tmp_path: Path, capsys):
    mirror = tmp_path / "mirror.git"
    subprocess.run(["git", "init", "--bare", str(mirror)], check=True, capture_output=True)
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init")
    _git(seed, "config", "user.email", "t@t")
    _git(seed, "config", "user.name", "test")
    (seed / ".onward" / "plans").mkdir(parents=True)
    (seed / ".onward" / "plans" / ".keep").write_text("x", encoding="utf-8")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-m", "seed")
    _git(seed, "remote", "add", "origin", str(mirror))
    _git(seed, "push", "-u", "origin", "HEAD")

    proj = tmp_path / "proj"
    proj.mkdir()
    assert cli.main(["init", "--root", str(proj)]) == 0
    repo_url = f"file://{mirror.resolve()}"
    _write_config_sync(proj, mode="repo", branch="onward", repo=repo_url, worktree_path=".onward/sync")

    assert cli.main(["new", "--root", str(proj), "plan", "Beta"]) == 0
    capsys.readouterr()
    assert cli.main(["sync", "--root", str(proj), "push"]) == 0
    capsys.readouterr()

    wt = proj / ".onward" / "sync"
    plan_in_wt = next((wt / ".onward" / "plans").glob("PLAN-*/plan.md"))
    plan_in_wt.write_text(
        plan_in_wt.read_text(encoding="utf-8").replace("open", "canceled"),
        encoding="utf-8",
    )
    _git(wt, "add", "-A")
    _git(wt, "commit", "-m", "remote edit")
    _git(wt, "push")

    assert cli.main(["sync", "--root", str(proj), "pull"]) == 0
    local_plan = next((proj / ".onward" / "plans").glob("PLAN-*/plan.md"))
    assert "canceled" in local_plan.read_text(encoding="utf-8")


def test_sync_push_local_mode_errors(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert cli.main(["sync", "--root", str(tmp_path), "push"]) == 1
    assert "local" in capsys.readouterr().out.lower()


def test_sync_pull_local_mode_errors(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert cli.main(["sync", "--root", str(tmp_path), "pull"]) == 1
    out = capsys.readouterr().out.lower()
    assert "local" in out


def test_doctor_warns_sync_repo_in_local_mode(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = (tmp_path / ".onward.config.yaml").read_text(encoding="utf-8")
    cfg = cfg.replace("repo: null", "repo: https://example.invalid/repo.git")
    (tmp_path / ".onward.config.yaml").write_text(cfg, encoding="utf-8")
    assert cli.main(["doctor", "--root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "sync.repo" in out and "local" in out.lower()


def test_doctor_flags_branch_mode_without_git(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = (tmp_path / ".onward.config.yaml").read_text(encoding="utf-8")
    cfg = cfg.replace("mode: local", "mode: branch")
    (tmp_path / ".onward.config.yaml").write_text(cfg, encoding="utf-8")

    assert cli.main(["doctor", "--root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "not a git repository" in out
