"""Tests for cross-root ID uniqueness in multi-root workspaces."""

from pathlib import Path

from onward import cli
from onward.artifacts import next_id, next_ids
from onward.config import WorkspaceLayout


def _init_default_workspace(root: Path) -> None:
    """Initialize a workspace with default .onward root."""
    assert cli.main(["init", "--root", str(root)]) == 0


def test_single_root_id_generation(tmp_path: Path):
    """In single-root mode, IDs should increment normally."""
    _init_default_workspace(tmp_path)

    # Create plans in single root
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Plan One"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Plan Two"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Plan Three"]) == 0

    # Verify IDs are sequential
    plans_dir = tmp_path / ".onward/plans"
    plan_dirs = sorted([p for p in plans_dir.iterdir() if p.is_dir() and p.name.startswith("PLAN-")])
    assert len(plan_dirs) == 3
    assert plan_dirs[0].name.startswith("PLAN-001-")
    assert plan_dirs[1].name.startswith("PLAN-002-")
    assert plan_dirs[2].name.startswith("PLAN-003-")


# NOTE: Multi-root CLI integration tests are skipped because they require
# require_workspace() in scaffold.py to be updated to be layout-aware.
# Currently, require_workspace() defaults to checking for ".onward/" even when
# a custom root or multi-root configuration is used. This is tracked in a
# separate task and is outside the scope of TASK-025.
#
# The core ID uniqueness logic is verified by the unit tests below
# (test_next_id_function_multi_root and test_next_ids_function_multi_root).


def test_next_id_function_multi_root(tmp_path: Path):
    """Direct test of next_id function in multi-root mode."""
    config = {"roots": {"proj_a": "./a", "proj_b": "./b"}}
    layout = WorkspaceLayout.from_config(tmp_path, config)

    # Create directories
    (tmp_path / "a/plans").mkdir(parents=True)
    (tmp_path / "b/plans").mkdir(parents=True)

    # Initially, first ID should be 001
    assert next_id(layout, "PLAN", "proj_a") == "PLAN-001"

    # Create a plan in project A
    plan_a_dir = tmp_path / "a/plans/PLAN-001-test"
    plan_a_dir.mkdir(parents=True)
    plan_a_path = plan_a_dir / "PLAN.md"
    plan_a_path.write_text(
        """---
id: PLAN-001
type: plan
project: proj_a
---
Test plan A
""",
        encoding="utf-8"
    )

    # Next ID should be 002, regardless of which project we're creating in
    assert next_id(layout, "PLAN", "proj_a") == "PLAN-002"
    assert next_id(layout, "PLAN", "proj_b") == "PLAN-002"

    # Create a plan in project B
    plan_b_dir = tmp_path / "b/plans/PLAN-002-test"
    plan_b_dir.mkdir(parents=True)
    plan_b_path = plan_b_dir / "PLAN.md"
    plan_b_path.write_text(
        """---
id: PLAN-002
type: plan
project: proj_b
---
Test plan B
""",
        encoding="utf-8"
    )

    # Next ID should be 003 in either project
    assert next_id(layout, "PLAN", "proj_a") == "PLAN-003"
    assert next_id(layout, "PLAN", "proj_b") == "PLAN-003"


def test_next_ids_function_multi_root(tmp_path: Path):
    """Direct test of next_ids function in multi-root mode."""
    config = {"roots": {"proj_a": "./a", "proj_b": "./b"}}
    layout = WorkspaceLayout.from_config(tmp_path, config)

    # Create directories
    (tmp_path / "a/plans").mkdir(parents=True)
    (tmp_path / "b/plans").mkdir(parents=True)

    # Request 3 IDs - should get sequential starting from 001
    ids = next_ids(layout, "TASK", 3, "proj_a")
    assert ids == ["TASK-001", "TASK-002", "TASK-003"]

    # Create task 001 in project A
    task_a_dir = tmp_path / "a/plans/tasks"
    task_a_dir.mkdir(parents=True)
    task_a_path = task_a_dir / "TASK-001-test.md"
    task_a_path.write_text(
        """---
id: TASK-001
type: task
project: proj_a
---
Test task A
""",
        encoding="utf-8"
    )

    # Create task 003 in project B (skipping 002)
    task_b_dir = tmp_path / "b/plans/tasks"
    task_b_dir.mkdir(parents=True)
    task_b_path = task_b_dir / "TASK-003-test.md"
    task_b_path.write_text(
        """---
id: TASK-003
type: task
project: proj_b
---
Test task B
""",
        encoding="utf-8"
    )

    # Request 2 more IDs - should get 002 and 004 (skipping 001 and 003)
    ids = next_ids(layout, "TASK", 2, "proj_a")
    assert ids == ["TASK-002", "TASK-004"]


def test_single_root_mode_scans_only_one_root(tmp_path: Path):
    """In single-root mode, next_id only scans the single root (optimization)."""
    config = {}  # Default .onward root
    layout = WorkspaceLayout.from_config(tmp_path, config)

    # Create directory
    (tmp_path / ".onward/plans").mkdir(parents=True)

    # Initially empty, should return 001
    assert next_id(layout, "PLAN") == "PLAN-001"

    # Create a plan
    plan_dir = tmp_path / ".onward/plans/PLAN-001-test"
    plan_dir.mkdir(parents=True)
    plan_path = plan_dir / "PLAN.md"
    plan_path.write_text(
        """---
id: PLAN-001
type: plan
---
Test plan
""",
        encoding="utf-8"
    )

    # Next should be 002
    assert next_id(layout, "PLAN") == "PLAN-002"

    # Even if we pass a project parameter in single-root mode, it's ignored
    # and we still scan the same root
    assert next_id(layout, "PLAN", "ignored") == "PLAN-002"
