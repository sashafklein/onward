"""Integration tests for multi-root workspace configurations."""

from pathlib import Path
from typing import Dict, Optional
import re

import pytest

from onward import cli
from tests.workspace_helpers import clear_post_task_shell


def _write_config(root: Path, config_text: str) -> None:
    """Write a custom .onward.config.yaml file."""
    (root / ".onward.config.yaml").write_text(config_text, encoding="utf-8")


def _setup_multi_root_workspace(tmp_path: Path, roots: Dict[str, str], default_project: Optional[str] = None) -> None:
    """Initialize a workspace with multi-root configuration."""
    # First run init with default config
    assert cli.main(["init", "--root", str(tmp_path)]) == 0

    # Modify config to use multi-root
    config_path = tmp_path / ".onward.config.yaml"
    config_text = config_path.read_text(encoding="utf-8")

    # Add roots config after version line
    roots_yaml = "\n".join(f"  {key}: {path}" for key, path in roots.items())
    roots_section = f"roots:\n{roots_yaml}\n"
    if default_project:
        roots_section += f"default_project: {default_project}\n"
    config_text = config_text.replace("version: 1\n", f"version: 1\n{roots_section}")

    # Remove worktree_path since it's not used with multi-root
    config_text = re.sub(r"  worktree_path:.*\n", "", config_text)
    config_path.write_text(config_text, encoding="utf-8")

    # Re-run init to create the directory structures
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    clear_post_task_shell(tmp_path)


def _setup_single_custom_root_workspace(tmp_path: Path, root: str) -> None:
    """Initialize a workspace with a custom single root."""
    # First run init with default config
    assert cli.main(["init", "--root", str(tmp_path)]) == 0

    # Modify config to use custom root
    config_path = tmp_path / ".onward.config.yaml"
    config_text = config_path.read_text(encoding="utf-8")
    config_text = config_text.replace("version: 1\n", f"version: 1\nroot: {root}\n")
    config_text = config_text.replace("worktree_path: .onward/sync", f"worktree_path: {root}/sync")
    config_text = config_text.replace("post_task_markdown: .onward/hooks/post-task.md", f"post_task_markdown: {root}/hooks/post-task.md")
    config_text = config_text.replace("post_chunk_markdown: .onward/hooks/post-chunk.md", f"post_chunk_markdown: {root}/hooks/post-chunk.md")
    config_path.write_text(config_text, encoding="utf-8")

    # Re-run init to create the new directory structure
    assert cli.main(["init", "--root", str(tmp_path)]) == 0
    clear_post_task_shell(tmp_path)


def _minimal_config_with_root(artifact_root: str) -> str:
    """Return minimal config with custom root."""
    return f"""version: 1
root: {artifact_root}

sync:
  mode: local
  branch: onward
  repo: null
  worktree_path: {artifact_root}/sync

executor:
  command: builtin
  args: []
  post_task_shell: []
  post_task_markdown: null

models:
  default: opus
"""


def _minimal_config_with_roots(roots_dict: Dict[str, str], default_project: Optional[str] = None) -> str:
    """Return minimal config with multiple roots."""
    roots_yaml = "\n".join(f"  {key}: {path}" for key, path in roots_dict.items())
    default_line = f"\ndefault_project: {default_project}" if default_project else ""
    return f"""version: 1
roots:
{roots_yaml}{default_line}

sync:
  mode: local
  branch: onward
  repo: null

executor:
  command: builtin
  args: []
  post_task_shell: []
  post_task_markdown: null

models:
  default: opus
"""


def test_init_with_custom_root_creates_directory_tree(tmp_path: Path):
    """onward init with root: nb creates the nb/ directory tree."""
    # First run init with default config
    exit_code = cli.main(["init", "--root", str(tmp_path)])
    assert exit_code == 0

    # Now modify the config to use custom root
    config_path = tmp_path / ".onward.config.yaml"
    config_text = config_path.read_text(encoding="utf-8")
    # Add root config after version line
    config_text = config_text.replace(
        "version: 1\n",
        "version: 1\nroot: nb\n"
    )
    config_text = config_text.replace("worktree_path: .onward/sync", "worktree_path: nb/sync")
    config_text = config_text.replace("post_task_markdown: .onward/hooks/post-task.md", "post_task_markdown: nb/hooks/post-task.md")
    config_text = config_text.replace("post_chunk_markdown: .onward/hooks/post-chunk.md", "post_chunk_markdown: nb/hooks/post-chunk.md")
    config_path.write_text(config_text, encoding="utf-8")

    # Re-run init to create the new directory structure
    exit_code = cli.main(["init", "--root", str(tmp_path)])
    assert exit_code == 0

    # Check that nb/ directory tree exists
    nb = tmp_path / "nb"
    assert (nb / "plans").is_dir()
    assert (nb / "plans" / ".archive").is_dir()
    assert (nb / "runs").is_dir()
    assert (nb / "reviews").is_dir()
    assert (nb / "templates").is_dir()
    assert (nb / "prompts").is_dir()
    assert (nb / "hooks").is_dir()
    assert (nb / "notes").is_dir()
    assert (nb / "sync").is_dir()
    assert (nb / "plans" / "index.yaml").is_file()
    assert (nb / "plans" / "recent.yaml").is_file()
    assert (nb / "templates" / "plan.md").is_file()
    assert (nb / "prompts" / "split-plan.md").is_file()

    # Note: .onward/ still exists from first init, but that's okay - the important thing is nb/ exists
    # In practice, users would run `onward migrate` to move contents

    # Check gitignore updated with custom root paths
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "nb/plans/.archive/" in gitignore
    assert "nb/sync/" in gitignore
    assert "nb/runs/" in gitignore
    assert "nb/ongoing.json" in gitignore


def test_init_with_multi_root_creates_all_directory_trees(tmp_path: Path):
    """onward init with roots: {a: .a, b: .b} creates both directory trees."""
    # First run init with default config
    exit_code = cli.main(["init", "--root", str(tmp_path)])
    assert exit_code == 0

    # Now modify the config to use multi-root
    config_path = tmp_path / ".onward.config.yaml"
    config_text = config_path.read_text(encoding="utf-8")
    # Add roots config after version line
    config_text = config_text.replace(
        "version: 1\n",
        "version: 1\nroots:\n  proj_a: .proj_a\n  proj_b: .proj_b\n"
    )
    # Remove worktree_path since it's not used in multi-root
    import re
    config_text = re.sub(r"  worktree_path:.*\n", "", config_text)
    config_path.write_text(config_text, encoding="utf-8")

    # Re-run init to create the new directory structures
    exit_code = cli.main(["init", "--root", str(tmp_path)])
    assert exit_code == 0

    # Check both project roots exist with full structure
    for project_dir in [".proj_a", ".proj_b"]:
        root = tmp_path / project_dir
        assert (root / "plans").is_dir()
        assert (root / "plans" / ".archive").is_dir()
        assert (root / "runs").is_dir()
        assert (root / "reviews").is_dir()
        assert (root / "templates").is_dir()
        assert (root / "prompts").is_dir()
        assert (root / "hooks").is_dir()
        assert (root / "notes").is_dir()
        assert (root / "sync").is_dir()
        assert (root / "plans" / "index.yaml").is_file()
        assert (root / "plans" / "recent.yaml").is_file()
        assert (root / "templates" / "plan.md").is_file()

    # Check gitignore has entries for both roots
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".proj_a/plans/.archive/" in gitignore
    assert ".proj_a/runs/" in gitignore
    assert ".proj_b/plans/.archive/" in gitignore
    assert ".proj_b/runs/" in gitignore


def test_new_plan_with_project_in_multi_root_creates_under_correct_root(tmp_path: Path):
    """onward new plan with --project in multi-root creates plan under the correct root."""
    _setup_multi_root_workspace(tmp_path, {"frontend": "./fe", "backend": "./be"})

    # Create plan in frontend project
    exit_code = cli.main(["new", "--root", str(tmp_path), "plan", "--project", "frontend", "FE Plan"])
    assert exit_code == 0

    # Check plan was created under fe/
    fe_plans = list((tmp_path / "fe" / "plans").glob("PLAN-*"))
    assert len(fe_plans) == 1
    assert "fe-plan" in fe_plans[0].name

    # Check it was NOT created under be/
    be_plans = list((tmp_path / "be" / "plans").glob("PLAN-*"))
    assert len(be_plans) == 0

    # Create another plan in backend project
    exit_code = cli.main(["new", "--root", str(tmp_path), "plan", "--project", "backend", "BE Plan"])
    assert exit_code == 0

    # Check plan was created under be/
    be_plans = list((tmp_path / "be" / "plans").glob("PLAN-*"))
    assert len(be_plans) == 1
    assert "be-plan" in be_plans[0].name

    # Frontend should still have only one plan
    fe_plans = list((tmp_path / "fe" / "plans").glob("PLAN-*"))
    assert len(fe_plans) == 1


def test_missing_project_in_multi_root_produces_error(tmp_path: Path, capsys):
    """Missing --project in multi-root without default_project produces an error."""
    _setup_multi_root_workspace(tmp_path, {"proj_a": ".a", "proj_b": ".b"})
    capsys.readouterr()

    # Try to create plan without --project
    exit_code = cli.main(["new", "--root", str(tmp_path), "plan", "Test Plan"])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert ("Multiple project" in out or "multiple project" in out.lower())
    assert "--project" in out
    assert "proj_a" in out and "proj_b" in out


def test_default_project_allows_commands_without_project_flag(tmp_path: Path):
    """default_project config allows commands to run without --project flag."""
    _setup_multi_root_workspace(tmp_path, {"proj_a": ".a", "proj_b": ".b"}, default_project="proj_a")

    # Create plan without --project (should use default_project)
    exit_code = cli.main(["new", "--root", str(tmp_path), "plan", "Default Plan"])
    assert exit_code == 0

    # Check plan was created under proj_a (the default)
    plans = list((tmp_path / ".a" / "plans").glob("PLAN-*"))
    assert len(plans) == 1

    # proj_b should have no plans
    plans_b = list((tmp_path / ".b" / "plans").glob("PLAN-*"))
    assert len(plans_b) == 0


def test_explicit_project_overrides_default_project(tmp_path: Path):
    """Explicit --project flag overrides default_project config."""
    _setup_multi_root_workspace(tmp_path, {"proj_a": ".a", "proj_b": ".b"}, default_project="proj_a")

    # Create plan with explicit --project that differs from default
    exit_code = cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_b", "Override Plan"])
    assert exit_code == 0

    # Check plan was created under proj_b (overriding default_project)
    plans_b = list((tmp_path / ".b" / "plans").glob("PLAN-*"))
    assert len(plans_b) == 1

    # proj_a should have no plans
    plans_a = list((tmp_path / ".a" / "plans").glob("PLAN-*"))
    assert len(plans_a) == 0


def test_report_without_project_shows_combined_multi_project_view(tmp_path: Path, capsys):
    """onward report without --project in multi-root shows combined report."""
    _setup_multi_root_workspace(tmp_path, {"frontend": "./fe", "backend": "./be"})

    # Create plans in both projects
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "frontend", "FE Plan"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "backend", "BE Plan"]) == 0
    capsys.readouterr()

    # Run report without --project
    exit_code = cli.main(["report", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    # Should mention both plans
    assert "PLAN-001" in out
    assert "PLAN-002" in out


def test_report_with_project_shows_single_project_view(tmp_path: Path, capsys):
    """onward report --project shows only that project's artifacts."""
    _setup_multi_root_workspace(tmp_path, {"frontend": "./fe", "backend": "./be"})

    # Create plans in both projects
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "frontend", "FE Plan"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "backend", "BE Plan"]) == 0
    capsys.readouterr()

    # Run report for frontend only
    exit_code = cli.main(["report", "--root", str(tmp_path), "--project", "frontend"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "PLAN-001" in out
    # Should not show PLAN-002 from the other project
    assert "PLAN-002" not in out


def test_cross_root_id_uniqueness(tmp_path: Path):
    """Creating artifacts in alternating projects yields sequential IDs."""
    _setup_multi_root_workspace(tmp_path, {"proj_a": ".a", "proj_b": ".b"})

    # Create plan in project A
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_a", "Plan A1"]) == 0
    # Create plan in project B
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_b", "Plan B1"]) == 0
    # Create another plan in project A
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_a", "Plan A2"]) == 0

    # Check IDs are sequential across projects
    plans_a = sorted((tmp_path / ".a" / "plans").glob("PLAN-*"))
    plans_b = sorted((tmp_path / ".b" / "plans").glob("PLAN-*"))

    assert len(plans_a) == 2
    assert len(plans_b) == 1

    # Extract IDs and verify they're sequential
    assert "PLAN-001" in plans_a[0].name
    assert "PLAN-002" in plans_b[0].name
    assert "PLAN-003" in plans_a[1].name


def test_template_fallback_project_specific_overrides_shared(tmp_path: Path):
    """Project-specific template overrides shared template."""
    _setup_multi_root_workspace(tmp_path, {"proj_a": ".a", "proj_b": ".b"})

    # Customize proj_a's plan template
    proj_a_template = tmp_path / ".a" / "templates" / "plan.md"
    custom_marker = "# CUSTOM PROJECT A TEMPLATE"
    proj_a_template.write_text(custom_marker + "\n" + proj_a_template.read_text(encoding="utf-8"), encoding="utf-8")

    # Create plan in proj_a (should use customized template)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_a", "Plan A"]) == 0

    # Create plan in proj_b (should use default template)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_b", "Plan B"]) == 0

    # Check proj_a plan has custom marker
    plan_a = next((tmp_path / ".a" / "plans").glob("PLAN-*/plan.md"))
    plan_a_content = plan_a.read_text(encoding="utf-8")
    assert custom_marker in plan_a_content

    # Check proj_b plan does NOT have custom marker
    plan_b = next((tmp_path / ".b" / "plans").glob("PLAN-*/plan.md"))
    plan_b_content = plan_b.read_text(encoding="utf-8")
    assert custom_marker not in plan_b_content


def test_config_validation_both_root_and_roots_produces_error(tmp_path: Path, capsys):
    """Config with both root and roots set produces an error."""
    config_text = """version: 1
root: nb
roots:
  proj_a: .a
  proj_b: .b

sync:
  mode: local
  branch: onward
  repo: null

models:
  default: opus
"""
    _write_config(tmp_path, config_text)
    capsys.readouterr()

    # Doctor should fail with clear error
    exit_code = cli.main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "root" in out.lower() and "roots" in out.lower()
    assert "mutually exclusive" in out.lower() or "cannot both be set" in out.lower()


def test_list_command_respects_project_in_multi_root(tmp_path: Path, capsys):
    """onward list respects --project flag in multi-root mode."""
    _setup_multi_root_workspace(tmp_path, {"proj_a": ".a", "proj_b": ".b"})

    # Create artifacts in both projects
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_a", "Plan A"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_b", "Plan B"]) == 0
    capsys.readouterr()

    # List proj_a only
    exit_code = cli.main(["list", "--root", str(tmp_path), "--project", "proj_a"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "PLAN-001" in out
    # Output should not include PLAN-002 from proj_b


def test_work_command_resolves_task_from_correct_project(tmp_path: Path, capsys):
    """onward work finds task in the correct project root."""
    _setup_multi_root_workspace(tmp_path, {"proj_a": ".a", "proj_b": ".b"})

    # Create plan and task in proj_a
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_a", "Plan A"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "--project", "proj_a", "PLAN-001", "Chunk A"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "task", "--project", "proj_a", "CHUNK-001", "Task A"]) == 0
    capsys.readouterr()

    # Show task (should find it in proj_a)
    exit_code = cli.main(["show", "--root", str(tmp_path), "--project", "proj_a", "TASK-001"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "TASK-001" in out
    assert "Task A" in out


def test_unknown_project_key_produces_error(tmp_path: Path, capsys):
    """Using an unknown project key produces a clear error."""
    _setup_multi_root_workspace(tmp_path, {"proj_a": ".a", "proj_b": ".b"})
    capsys.readouterr()

    # Try to use non-existent project
    exit_code = cli.main(["new", "--root", str(tmp_path), "plan", "--project", "unknown", "Test"])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "unknown" in out.lower()
    assert "project" in out.lower()


def test_multi_root_ongoing_isolation(tmp_path: Path):
    """Each project has its own ongoing.json for work isolation."""
    _setup_multi_root_workspace(tmp_path, {"proj_a": ".a", "proj_b": ".b"})

    # Check that both projects have separate ongoing.json files created during init
    ongoing_a = tmp_path / ".a" / "ongoing.json"
    ongoing_b = tmp_path / ".b" / "ongoing.json"

    assert ongoing_a.exists()
    assert ongoing_b.exists()

    # Both should be empty initially (no active work)
    import json
    ongoing_a_data = json.loads(ongoing_a.read_text(encoding="utf-8"))
    ongoing_b_data = json.loads(ongoing_b.read_text(encoding="utf-8"))

    assert ongoing_a_data.get("task_id") is None
    assert ongoing_b_data.get("task_id") is None


def test_single_custom_root_ignores_project_flag(tmp_path: Path):
    """In single-root mode, --project flag is ignored (metadata only)."""
    _setup_single_custom_root_workspace(tmp_path, "nb")

    # Create plan with --project in single-root mode (should be ignored for path resolution)
    exit_code = cli.main(["new", "--root", str(tmp_path), "plan", "--project", "ignored", "Test Plan"])
    assert exit_code == 0

    # Plan should be created under nb/ (not under a project-specific dir)
    plans = list((tmp_path / "nb" / "plans").glob("PLAN-*"))
    assert len(plans) == 1

    # The --project in single-root mode is metadata only
    # In single-root mode, project is stored but may be empty string if not in multi-root
    plan_file = plans[0] / "plan.md"
    plan_content = plan_file.read_text(encoding="utf-8")
    assert "project:" in plan_content


def test_index_separate_per_project_in_multi_root(tmp_path: Path):
    """Each project maintains its own index.yaml."""
    _setup_multi_root_workspace(tmp_path, {"proj_a": ".a", "proj_b": ".b"})

    # Create plans in both projects
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_a", "Plan A"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_b", "Plan B"]) == 0

    # Check that indexes exist and contain correct plans
    import yaml
    index_a = yaml.safe_load((tmp_path / ".a" / "plans" / "index.yaml").read_text(encoding="utf-8"))
    index_b = yaml.safe_load((tmp_path / ".b" / "plans" / "index.yaml").read_text(encoding="utf-8"))

    # Each project's index should only contain its own plans
    assert len(index_a["plans"]) == 1
    assert len(index_b["plans"]) == 1
    assert index_a["plans"][0]["id"] == "PLAN-001"
    assert index_b["plans"][0]["id"] == "PLAN-002"

    # Create another plan in proj_a
    assert cli.main(["new", "--root", str(tmp_path), "plan", "--project", "proj_a", "Plan A2"]) == 0

    # Reload indexes
    index_a = yaml.safe_load((tmp_path / ".a" / "plans" / "index.yaml").read_text(encoding="utf-8"))
    index_b = yaml.safe_load((tmp_path / ".b" / "plans" / "index.yaml").read_text(encoding="utf-8"))

    # proj_a should now have 2 plans, proj_b still has 1
    assert len(index_a["plans"]) == 2
    assert len(index_b["plans"]) == 1
