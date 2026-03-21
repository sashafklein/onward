"""Tests for CHUNK-012 scale/ergonomics: batch tasks, ready, effort, project resolution, index fast path."""

from __future__ import annotations

import json
from pathlib import Path

from onward import cli
from onward.artifacts import (
    collect_artifacts,
    load_index,
    parse_artifact,
    regenerate_indexes,
    resolve_project,
)
from onward.util import normalize_effort
from tests.conftest import make_default_layout


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def _null_post_chunk_hook(root: Path) -> None:
    p = root / ".onward.config.yaml"
    raw = p.read_text(encoding="utf-8")
    raw = raw.replace(
        "post_chunk_markdown: .onward/hooks/post-chunk.md",
        "post_chunk_markdown: null",
    )
    p.write_text(raw, encoding="utf-8")


def test_normalize_effort_case_insensitive() -> None:
    assert normalize_effort("M") == "m"
    assert normalize_effort("invalid") == ""


def test_batch_creates_tasks_sequential_ids(tmp_path: Path, capsys) -> None:
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "P"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    batch = tmp_path / "batch.json"
    batch.write_text(
        json.dumps(
            [
                {"title": "First", "description": "d1"},
                {"title": "Second", "description": "d2"},
            ]
        ),
        encoding="utf-8",
    )
    assert (
        cli.main(
            ["new", "--root", str(tmp_path), "task", "CHUNK-001", "--batch", str(batch)]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "TASK-001" in out and "TASK-002" in out
    arts = collect_artifacts(make_default_layout(tmp_path))
    ids = sorted(str(a.metadata.get("id", "")) for a in arts if str(a.metadata.get("type", "")) == "task")
    assert ids == ["TASK-001", "TASK-002"]


def test_batch_intra_batch_depends(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "P"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    batch = tmp_path / "batch.json"
    batch.write_text(
        json.dumps(
            [
                {"title": "A", "description": "a"},
                {"title": "B", "description": "b", "depends_on": ["$0"]},
            ]
        ),
        encoding="utf-8",
    )
    assert (
        cli.main(
            ["new", "--root", str(tmp_path), "task", "CHUNK-001", "--batch", str(batch)]
        )
        == 0
    )
    t2 = next(p for p in tmp_path.glob(".onward/plans/**/tasks/TASK-002-*.md"))
    art = parse_artifact(t2)
    assert art.metadata.get("depends_on") == ["TASK-001"]


def test_batch_invalid_entry_errors(tmp_path: Path, capsys) -> None:
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "P"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps([{"title": "Only title", "description": ""}]), encoding="utf-8")
    assert (
        cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "--batch", str(batch)])
        == 1
    )
    assert "description" in capsys.readouterr().out


def test_batch_empty_errors(tmp_path: Path, capsys) -> None:
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "P"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    batch = tmp_path / "batch.json"
    batch.write_text("[]", encoding="utf-8")
    assert (
        cli.main(["new", "--root", str(tmp_path), "task", "CHUNK-001", "--batch", str(batch)])
        == 1
    )
    assert "empty" in capsys.readouterr().out.lower()


def test_ready_shows_actionable_tasks(tmp_path: Path, capsys) -> None:
    _init_workspace(tmp_path)
    _null_post_chunk_hook(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "Alpha"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    assert (
        cli.main(
            [
                "new",
                "--root",
                str(tmp_path),
                "task",
                "CHUNK-001",
                "Do work",
                "--description",
                "x",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert cli.main(["ready", "--root", str(tmp_path), "--no-color"]) == 0
    out = capsys.readouterr().out
    assert "TASK-001" in out and "Do work" in out


def test_ready_no_tasks_message(tmp_path: Path, capsys) -> None:
    _init_workspace(tmp_path)
    _null_post_chunk_hook(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "P"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    capsys.readouterr()
    assert cli.main(["ready", "--root", str(tmp_path)]) == 0
    assert "No ready tasks" in capsys.readouterr().out


def test_new_task_effort_stored(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "P"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    assert (
        cli.main(
            [
                "new",
                "--root",
                str(tmp_path),
                "task",
                "CHUNK-001",
                "T",
                "--description",
                "d",
                "--effort",
                "m",
            ]
        )
        == 0
    )
    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    art = parse_artifact(task_path)
    assert art.metadata.get("effort") == "m"


def test_project_inheritance_on_new_chunk_and_task(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    assert (
        cli.main(
            ["new", "--root", str(tmp_path), "plan", "P", "--project", "myapp"]
        )
        == 0
    )
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    chunk_path = next(tmp_path.glob(".onward/plans/**/chunks/CHUNK-001-*.md"))
    assert 'project: "myapp"' in chunk_path.read_text(encoding="utf-8")

    assert (
        cli.main(
            [
                "new",
                "--root",
                str(tmp_path),
                "task",
                "CHUNK-001",
                "T",
                "--description",
                "d",
            ]
        )
        == 0
    )
    task_path = next(tmp_path.glob(".onward/plans/**/tasks/TASK-001-*.md"))
    assert 'project: "myapp"' in task_path.read_text(encoding="utf-8")


def test_resolve_project_inherited_for_filter(tmp_path: Path, capsys) -> None:
    _init_workspace(tmp_path)
    assert (
        cli.main(
            ["new", "--root", str(tmp_path), "plan", "P", "--project", "myapp"]
        )
        == 0
    )
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    assert (
        cli.main(
            [
                "new",
                "--root",
                str(tmp_path),
                "task",
                "CHUNK-001",
                "T",
                "--description",
                "d",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert cli.main(["list", "--root", str(tmp_path), "--project", "myapp"]) == 0
    out = capsys.readouterr().out
    assert "TASK-001" in out


def test_index_version_increments(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    layout = make_default_layout(tmp_path)
    idx1 = load_index(layout)
    assert idx1 is not None
    v1 = idx1.get("index_version")
    assert isinstance(v1, int) and v1 >= 1
    regenerate_indexes(layout)
    idx2 = load_index(layout)
    assert idx2 is not None and idx2.get("index_version") == v1 + 1


def test_resolve_project_walks_hierarchy(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    assert cli.main(["new", "--root", str(tmp_path), "plan", "P"]) == 0
    assert cli.main(["new", "--root", str(tmp_path), "chunk", "PLAN-001", "C"]) == 0
    assert (
        cli.main(
            [
                "new",
                "--root",
                str(tmp_path),
                "task",
                "CHUNK-001",
                "T",
                "--description",
                "d",
            ]
        )
        == 0
    )
    arts = collect_artifacts(make_default_layout(tmp_path))
    by_id = {str(a.metadata.get("id", "")): a for a in arts if a.metadata.get("id")}
    task = by_id["TASK-001"]
    assert resolve_project(task, by_id) == ""
