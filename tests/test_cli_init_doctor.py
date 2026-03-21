from pathlib import Path

from onward import cli
from onward.config import config_raw_deprecation_warnings


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
    assert "# Executor command for `onward work`, markdown hooks, and `review-plan`." in config
    assert "# Split decomposition; blank falls back through split -> default." in config


def test_doctor_passes_after_init(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Doctor check passed" in out


def test_doctor_warns_on_blocked_by_frontmatter(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "Build"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "T"]) == 0
    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    raw = task_path.read_text(encoding="utf-8")
    task_path.write_text(
        raw.replace("depends_on: []", "depends_on: []\nblocked_by:\n  - TASK-999"),
        encoding="utf-8",
    )
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "deprecated" in out
    assert "blocked_by" in out
    assert "Doctor check passed" in out


def test_doctor_fails_on_invalid_ongoing_json(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    (tmp_path / ".onward/ongoing.json").write_text("{not json", encoding="utf-8")

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "invalid json in .onward/ongoing.json" in out


def test_doctor_fails_on_unknown_config_key(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + "\nunknown_top_level: true\n", encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "unknown_top_level" in out


def test_doctor_fails_on_removed_pre_task_markdown_hook(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    raw = cfg.read_text(encoding="utf-8")
    raw = raw.replace(
        "  post_chunk_markdown:",
        "  pre_task_markdown: null\n  post_chunk_markdown:",
        1,
    )
    cfg.write_text(raw, encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "pre_task_markdown" in out


def test_doctor_fails_on_unknown_nested_config_key(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    raw = cfg.read_text(encoding="utf-8")
    raw = raw.replace("  review_1: codex-latest\n", "  review_1: codex-latest\n  typo_key: x\n")
    cfg.write_text(raw, encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "models.typo_key" in out


def test_doctor_warns_when_models_default_missing(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    raw = cfg.read_text(encoding="utf-8")
    raw = raw.replace(
        "  # Ultimate fallback and baseline tier (required logically; empty uses opus-latest).\n  default: opus-latest\n",
        "",
        1,
    )
    cfg.write_text(raw, encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "models.default is unset" in out
    assert "Doctor check passed" in out


def test_doctor_fails_on_removed_path_key(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + "\npath: elsewhere\n", encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "unsupported config key 'path'" in out


def test_doctor_fails_on_removed_work_worktree_keys(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    raw = cfg.read_text(encoding="utf-8")
    cfg.write_text(raw.replace("work:\n", "work:\n  create_worktree: true\n", 1), encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "work.create_worktree" in out


def test_doctor_fails_on_sync_local_with_repo_url(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace("repo: null", "repo: https://example.com/r.git"), encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert 'sync.mode is "local"' in out


def test_doctor_fails_when_executor_args_not_list(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace("args: []", "args: not-a-list"), encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "executor.args must be a list" in out


def test_doctor_warns_on_legacy_ralph_key_only(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    text = cfg.read_text(encoding="utf-8")
    text = text.replace("executor:", "ralph:", 1)
    cfg.write_text(text, encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "deprecated" in out
    assert "ralph" in out


def test_doctor_warns_on_legacy_model_keys(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    raw = cfg.read_text(encoding="utf-8")
    raw = raw.replace(
        "models:",
        "models:\n  split_default: sonnet-4-6\n  review_default: opus-latest\n  task_default: haiku-latest\n",
        1,
    )
    cfg.write_text(raw, encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "deprecated" in out
    assert "split_default" in out
    assert "review_default" in out
    assert "task_default" in out
    assert "Doctor check passed" in out


def test_doctor_warns_when_split_and_split_default_both_set(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    raw = cfg.read_text(encoding="utf-8")
    # Non-empty split + split_default triggers the conflict warning (empty split does not).
    raw = raw.replace(
        "  split:\n",
        "  split: sonnet-4-6\n  split_default: legacy-model\n",
        1,
    )
    cfg.write_text(raw, encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "split_default" in out
    assert "ignored" in out


def test_config_raw_deprecation_split_only_no_duplicate_conflict_message() -> None:
    """Only split_default set should not emit the 'ignored because split is set' line."""
    msgs = config_raw_deprecation_warnings(
        {"models": {"default": "D", "split_default": "sonnet-4-6"}},
    )
    assert any("rename to models.split" in m for m in msgs)
    assert not any("ignored because models.split" in m for m in msgs)


def test_doctor_warns_when_both_ralph_and_executor(tmp_path: Path, capsys):
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    cfg = tmp_path / ".onward.config.yaml"
    text = cfg.read_text(encoding="utf-8")
    insert = "\nralph:\n  command: onward-exec\n  args: []\n  enabled: true\n"
    text = text.replace("\nmodels:", insert + "\nmodels:", 1)
    cfg.write_text(text, encoding="utf-8")
    capsys.readouterr()

    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "ignored" in out or "deprecated" in out


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
