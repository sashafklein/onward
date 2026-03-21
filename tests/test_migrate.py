"""Tests for the onward migrate command."""
from pathlib import Path

from onward import cli


def test_migrate_basic_custom_root(tmp_path: Path, capsys):
    """Test basic migration from .onward/ to a custom root."""
    # Initialize with default .onward
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    # Create some content
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Test Plan"]) == 0
    capsys.readouterr()

    # Verify .onward exists
    assert (tmp_path / ".onward/plans").exists()
    assert (tmp_path / ".onward/plans/PLAN-001-test-plan").exists()

    # Update config to use custom root
    config_path = tmp_path / ".onward.config.yaml"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(f"root: nb\n{config}", encoding="utf-8")

    # Run migrate
    exit_code = cli.main(["migrate", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Moved: .onward/plans → nb/plans" in out
    assert "Migration complete" in out

    # Verify new structure exists
    assert (tmp_path / "nb/plans").exists()
    assert (tmp_path / "nb/plans/PLAN-001-test-plan").exists()

    # Verify old structure is gone
    assert not (tmp_path / ".onward").exists() or not any((tmp_path / ".onward").iterdir())

    # Verify .gitignore was updated
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "nb/plans/.archive/" in gitignore
    assert "nb/sync/" in gitignore
    assert "nb/runs/" in gitignore
    assert "nb/ongoing.json" in gitignore

    # Verify doctor passes
    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Doctor check passed" in out


def test_migrate_dry_run(tmp_path: Path, capsys):
    """Test --dry-run mode doesn't modify filesystem."""
    # Initialize with default .onward
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Test"]) == 0
    capsys.readouterr()

    # Update config to use custom root
    config_path = tmp_path / ".onward.config.yaml"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(f"root: nb\n{config}", encoding="utf-8")

    # Run migrate with --dry-run
    exit_code = cli.main(["migrate", "--root", str(tmp_path), "--dry-run"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Would move: .onward/plans → nb/plans" in out
    assert "Dry run:" in out

    # Verify filesystem unchanged
    assert (tmp_path / ".onward/plans").exists()
    assert (tmp_path / ".onward/plans/PLAN-001-test").exists()
    assert not (tmp_path / "nb/plans/PLAN-001-test").exists()


def test_migrate_force_overwrite(tmp_path: Path, capsys):
    """Test --force flag allows overwriting existing content."""
    # Initialize with default .onward
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Old Plan"]) == 0
    capsys.readouterr()

    # Create target directory with existing content
    (tmp_path / "nb/plans").mkdir(parents=True)
    (tmp_path / "nb/plans/existing.txt").write_text("existing", encoding="utf-8")

    # Update config to use custom root
    config_path = tmp_path / ".onward.config.yaml"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(f"root: nb\n{config}", encoding="utf-8")

    # Try migrate without --force (should fail)
    exit_code = cli.main(["migrate", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "already has content" in out
    assert "--force" in out

    # Try with --force (should succeed)
    exit_code = cli.main(["migrate", "--root", str(tmp_path), "--force"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Migration complete" in out

    # Verify migration happened
    assert (tmp_path / "nb/plans/PLAN-001-old-plan").exists()


def test_migrate_multi_root_requires_project(tmp_path: Path, capsys):
    """Test that multi-root mode requires --project flag."""
    # Initialize with default .onward
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    # Update config for multi-root mode
    config_path = tmp_path / ".onward.config.yaml"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(f"roots:\n  alpha: ./alpha\n  beta: ./beta\n{config}", encoding="utf-8")

    # Try migrate without --project (should fail)
    exit_code = cli.main(["migrate", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "Multiple projects configured" in out
    assert "--project" in out


def test_migrate_multi_root_with_project(tmp_path: Path, capsys):
    """Test migration to specific project root in multi-root mode."""
    # Initialize with default .onward
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha Plan"]) == 0
    capsys.readouterr()

    # Update config for multi-root mode
    config_path = tmp_path / ".onward.config.yaml"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(f"roots:\n  alpha: ./alpha\n  beta: ./beta\n{config}", encoding="utf-8")

    # Migrate to alpha project
    exit_code = cli.main(["migrate", "--root", str(tmp_path), "--project", "alpha"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Moved: .onward/plans → alpha/plans" in out

    # Verify migration
    assert (tmp_path / "alpha/plans/PLAN-001-alpha-plan").exists()
    assert not (tmp_path / ".onward").exists() or not any((tmp_path / ".onward").iterdir())


def test_migrate_source_equals_target_is_noop(tmp_path: Path, capsys):
    """Test that migrating when source == target is a no-op."""
    # Initialize with default .onward
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    # Config already has .onward as default (no root specified means .onward)
    # Try to migrate
    exit_code = cli.main(["migrate", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "source and target are the same" in out


def test_migrate_no_source_is_noop(tmp_path: Path, capsys):
    """Test that migration is a no-op if source doesn't exist."""
    # Initialize with custom root from the start (no .onward created)
    config_path = tmp_path / ".onward.config.yaml"
    config_path.write_text("root: nb\nversion: 1\n", encoding="utf-8")

    # Initialize
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    # Try to migrate (should be no-op since .onward doesn't exist)
    exit_code = cli.main(["migrate", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Nothing to migrate" in out or "not found" in out


def test_migrate_idempotent(tmp_path: Path, capsys):
    """Test that running migrate twice is safe (idempotent)."""
    # Initialize with default .onward
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Test"]) == 0
    capsys.readouterr()

    # Update config to use custom root
    config_path = tmp_path / ".onward.config.yaml"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(f"root: nb\n{config}", encoding="utf-8")

    # First migration
    assert cli.main(["migrate", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    # Second migration (should be no-op)
    exit_code = cli.main(["migrate", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Nothing to migrate" in out or "not found" in out or "already migrated" in out


def test_migrate_updates_gitignore_entries(tmp_path: Path, capsys):
    """Test that .gitignore entries are properly updated from old to new root."""
    # Initialize with default .onward
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    # Verify initial .gitignore has old entries
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".onward/plans/.archive/" in gitignore
    assert ".onward/sync/" in gitignore

    # Update config to use custom root
    config_path = tmp_path / ".onward.config.yaml"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(f"root: plans\n{config}", encoding="utf-8")

    # Migrate
    assert cli.main(["migrate", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    # Verify .gitignore was updated
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "plans/plans/.archive/" in gitignore
    assert "plans/sync/" in gitignore
    assert "plans/runs/" in gitignore
    assert "plans/ongoing.json" in gitignore

    # Old entries should be replaced (not duplicated)
    assert gitignore.count("plans/.archive/") == 1  # Only one occurrence


def test_migrate_preserves_artifact_content(tmp_path: Path, capsys):
    """Test that artifact content is preserved during migration."""
    # Initialize and create artifacts
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Test Plan"]) == 0
    capsys.readouterr()

    # Get original plan content (plans are directories with PLAN.md inside)
    original_plan_dir = next((tmp_path / ".onward/plans").glob("PLAN-*"))
    original_plan_file = original_plan_dir / "PLAN.md"
    original_content = original_plan_file.read_text(encoding="utf-8")

    # Update config and migrate
    config_path = tmp_path / ".onward.config.yaml"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(f"root: nb\n{config}", encoding="utf-8")
    assert cli.main(["migrate", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    # Verify content is preserved
    migrated_plan_dir = next((tmp_path / "nb/plans").glob("PLAN-*"))
    migrated_plan_file = migrated_plan_dir / "PLAN.md"
    migrated_content = migrated_plan_file.read_text(encoding="utf-8")
    assert migrated_content == original_content


def test_migrate_with_runs_and_reviews(tmp_path: Path, capsys):
    """Test migration with runs and reviews directories."""
    # Initialize
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    # Create some content in runs and reviews
    (tmp_path / ".onward/runs").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".onward/runs/run-001.json").write_text('{"test": "data"}', encoding="utf-8")
    (tmp_path / ".onward/reviews").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".onward/reviews/review-001.md").write_text("# Review", encoding="utf-8")

    # Update config and migrate
    config_path = tmp_path / ".onward.config.yaml"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(f"root: nb\n{config}", encoding="utf-8")

    exit_code = cli.main(["migrate", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Moved: .onward/runs → nb/runs" in out
    assert "Moved: .onward/reviews → nb/reviews" in out

    # Verify content was moved
    assert (tmp_path / "nb/runs/run-001.json").exists()
    assert (tmp_path / "nb/reviews/review-001.md").exists()
    assert (tmp_path / "nb/runs/run-001.json").read_text(encoding="utf-8") == '{"test": "data"}'
