"""Tests for WorkspaceLayout path resolution."""

from pathlib import Path

import pytest

from onward.config import WorkspaceLayout


def test_default_layout_when_no_config(tmp_path: Path):
    """When neither root nor roots is set, should default to .onward/."""
    layout = WorkspaceLayout.from_config(tmp_path, {})

    assert not layout.is_multi_root
    assert layout.all_project_keys() == [None]
    assert layout.artifact_root() == tmp_path / ".onward"
    assert layout.plans_dir() == tmp_path / ".onward/plans"
    assert layout.runs_dir() == tmp_path / ".onward/runs"
    assert layout.reviews_dir() == tmp_path / ".onward/reviews"
    assert layout.templates_dir() == tmp_path / ".onward/templates"
    assert layout.prompts_dir() == tmp_path / ".onward/prompts"
    assert layout.hooks_dir() == tmp_path / ".onward/hooks"
    assert layout.notes_dir() == tmp_path / ".onward/notes"
    assert layout.sync_dir() == tmp_path / ".onward/sync"
    assert layout.ongoing_path() == tmp_path / ".onward/ongoing.json"
    assert layout.index_path() == tmp_path / ".onward/plans/index.yaml"
    assert layout.recent_path() == tmp_path / ".onward/plans/recent.yaml"
    assert layout.archive_dir() == tmp_path / ".onward/plans/.archive"


def test_single_custom_root_relative(tmp_path: Path):
    """When root: nb is set, all artifacts live under nb/."""
    layout = WorkspaceLayout.from_config(tmp_path, {"root": "nb"})

    assert not layout.is_multi_root
    assert layout.all_project_keys() == [None]
    assert layout.artifact_root() == tmp_path / "nb"
    assert layout.plans_dir() == tmp_path / "nb/plans"
    assert layout.runs_dir() == tmp_path / "nb/runs"
    assert layout.ongoing_path() == tmp_path / "nb/ongoing.json"
    assert layout.index_path() == tmp_path / "nb/plans/index.yaml"
    assert layout.recent_path() == tmp_path / "nb/plans/recent.yaml"


def test_single_custom_root_absolute(tmp_path: Path):
    """When root is an absolute path, use it directly."""
    custom_root = tmp_path / "custom" / "artifacts"
    layout = WorkspaceLayout.from_config(tmp_path, {"root": str(custom_root)})

    assert not layout.is_multi_root
    assert layout.artifact_root() == custom_root
    assert layout.plans_dir() == custom_root / "plans"


def test_multi_root_mode(tmp_path: Path):
    """When roots: {a: .a, b: .b} is set, resolve per-project paths."""
    layout = WorkspaceLayout.from_config(
        tmp_path,
        {"roots": {"frontend": "./fe", "backend": "./be"}},
    )

    assert layout.is_multi_root
    assert set(layout.all_project_keys()) == {"frontend", "backend"}

    # Frontend project
    assert layout.artifact_root("frontend") == tmp_path / "fe"
    assert layout.plans_dir("frontend") == tmp_path / "fe/plans"
    assert layout.runs_dir("frontend") == tmp_path / "fe/runs"
    assert layout.ongoing_path("frontend") == tmp_path / "fe/ongoing.json"

    # Backend project
    assert layout.artifact_root("backend") == tmp_path / "be"
    assert layout.plans_dir("backend") == tmp_path / "be/plans"
    assert layout.runs_dir("backend") == tmp_path / "be/runs"
    assert layout.ongoing_path("backend") == tmp_path / "be/ongoing.json"


def test_multi_root_without_project_raises(tmp_path: Path):
    """In multi-root mode without default_project, must provide project arg."""
    layout = WorkspaceLayout.from_config(
        tmp_path,
        {"roots": {"a": "./a", "b": "./b"}},
    )

    with pytest.raises(ValueError, match="Multiple projects configured"):
        layout.artifact_root()

    with pytest.raises(ValueError, match="Multiple projects configured"):
        layout.plans_dir()


def test_multi_root_with_default_project(tmp_path: Path):
    """When default_project is set, use it when project arg is None."""
    layout = WorkspaceLayout.from_config(
        tmp_path,
        {"roots": {"a": "./a", "b": "./b"}, "default_project": "a"},
    )

    assert layout.default_project == "a"
    # No project arg should use default
    assert layout.artifact_root() == tmp_path / "a"
    assert layout.plans_dir() == tmp_path / "a/plans"

    # Explicit project arg overrides default
    assert layout.artifact_root("b") == tmp_path / "b"
    assert layout.plans_dir("b") == tmp_path / "b/plans"


def test_multi_root_unknown_project_raises(tmp_path: Path):
    """Requesting an unknown project key raises ValueError."""
    layout = WorkspaceLayout.from_config(
        tmp_path,
        {"roots": {"a": "./a", "b": "./b"}},
    )

    with pytest.raises(ValueError, match="Unknown project 'unknown'"):
        layout.artifact_root("unknown")


def test_single_root_ignores_project_arg(tmp_path: Path):
    """In single-root mode, project arg is ignored (for uniform API)."""
    layout = WorkspaceLayout.from_config(tmp_path, {"root": "nb"})

    # Should return the same path regardless of project arg
    assert layout.artifact_root() == tmp_path / "nb"
    assert layout.artifact_root("anything") == tmp_path / "nb"
    assert layout.plans_dir("ignored") == tmp_path / "nb/plans"


def test_empty_root_string_falls_back_to_default(tmp_path: Path):
    """Empty root string should fall back to default .onward."""
    layout = WorkspaceLayout.from_config(tmp_path, {"root": ""})

    assert layout.artifact_root() == tmp_path / ".onward"


def test_empty_roots_dict_falls_back_to_default(tmp_path: Path):
    """Empty roots dict should fall back to default .onward."""
    layout = WorkspaceLayout.from_config(tmp_path, {"roots": {}})

    assert not layout.is_multi_root
    assert layout.artifact_root() == tmp_path / ".onward"


def test_roots_with_empty_values_skipped(tmp_path: Path):
    """Empty path values in roots dict are skipped."""
    layout = WorkspaceLayout.from_config(
        tmp_path,
        {"roots": {"a": "./a", "empty": "", "b": "./b"}},
    )

    assert set(layout.all_project_keys()) == {"a", "b"}


def test_all_directory_methods(tmp_path: Path):
    """Verify all directory resolution methods work correctly."""
    layout = WorkspaceLayout.from_config(tmp_path, {"root": "custom"})

    base = tmp_path / "custom"
    assert layout.artifact_root() == base
    assert layout.plans_dir() == base / "plans"
    assert layout.runs_dir() == base / "runs"
    assert layout.reviews_dir() == base / "reviews"
    assert layout.templates_dir() == base / "templates"
    assert layout.prompts_dir() == base / "prompts"
    assert layout.hooks_dir() == base / "hooks"
    assert layout.notes_dir() == base / "notes"
    assert layout.sync_dir() == base / "sync"
    assert layout.ongoing_path() == base / "ongoing.json"
    assert layout.index_path() == base / "plans/index.yaml"
    assert layout.recent_path() == base / "plans/recent.yaml"
    assert layout.archive_dir() == base / "plans/.archive"


def test_workspace_root_preserved(tmp_path: Path):
    """WorkspaceLayout preserves the workspace root path."""
    layout = WorkspaceLayout.from_config(tmp_path, {})

    assert layout.workspace_root == tmp_path


def test_invalid_config_type_falls_back_to_default(tmp_path: Path):
    """Non-dict config should fall back to default .onward."""
    layout = WorkspaceLayout.from_config(tmp_path, "not a dict")  # type: ignore

    assert layout.artifact_root() == tmp_path / ".onward"


def test_invalid_roots_type_falls_back_to_default(tmp_path: Path):
    """Non-dict roots value should fall back to default .onward."""
    layout = WorkspaceLayout.from_config(tmp_path, {"roots": "not a dict"})

    assert layout.artifact_root() == tmp_path / ".onward"
