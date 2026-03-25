"""Fail CI when high-level docs omit a leaf CLI command from build_parser()."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from onward.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]
DOC_PATHS = (
    ROOT / "README.md",
    ROOT / "INSTALLATION.md",
    ROOT / "docs" / "CONTRIBUTION.md",
)


def _subparsers_actions(parser: argparse.ArgumentParser) -> list[argparse.Action]:
    return [a for a in parser._actions if type(a).__name__ == "_SubParsersAction"]


def collect_leaf_cli_commands(parser: argparse.ArgumentParser) -> list[str]:
    """Leaf user invocations, e.g. ``new plan``, ``sync pull``, ``init``."""
    out: list[str] = []
    for sp in _subparsers_actions(parser):
        for name, sub in sorted(sp.choices.items()):
            inner = _subparsers_actions(sub)
            if inner:
                for subname in sorted(inner[0].choices.keys()):
                    out.append(f"{name} {subname}")
            else:
                out.append(name)
    return sorted(out)


def _pattern_for_leaf(leaf: str) -> re.Pattern[str]:
    parts = leaf.split()
    tail = r"\s+".join(re.escape(p) for p in parts)
    return re.compile(r"onward\s+" + tail, re.IGNORECASE)


@pytest.fixture(scope="module")
def leaf_commands() -> list[str]:
    return collect_leaf_cli_commands(build_parser())


@pytest.mark.parametrize("doc_path", DOC_PATHS, ids=lambda p: p.name)
def test_leaf_commands_in_each_canonical_doc(
    doc_path: Path, leaf_commands: list[str]
) -> None:
    """Each high-level guide must mention every leaf so none goes stale in isolation."""
    text = doc_path.read_text(encoding="utf-8")
    failures = [leaf for leaf in leaf_commands if not _pattern_for_leaf(leaf).search(text)]
    assert not failures, (
        f"{doc_path.relative_to(ROOT)} missing explicit `onward …` for: "
        + ", ".join(failures)
        + "\nUse full spellings (e.g. `onward complete`, not only `start|complete|cancel`)."
    )


def test_collect_leaf_commands_matches_known_set(leaf_commands: list[str]) -> None:
    """Guardrail if argparse structure changes without updating this test's intent."""
    expected = [
        "archive",
        "cancel",
        "complete",
        "doctor",
        "init",
        "linear push",
        "list",
        "migrate",
        "new chunk",
        "new plan",
        "new task",
        "next",
        "note",
        "one-off",
        "progress",
        "ready",
        "recent",
        "report",
        "retry",
        "review-plan",
        "roadmap",
        "show",
        "split",
        "sync pull",
        "sync push",
        "sync status",
        "tree",
        "work",
    ]
    assert leaf_commands == expected
