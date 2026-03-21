"""Tests for markdown report output (--md flag)."""
from pathlib import Path
import re

from onward import cli


def _init_workspace(root: Path) -> None:
    assert cli.main(["init", "--root", str(root)]) == 0


def _create_test_artifacts(root: Path) -> None:
    """Create a mix of plans, chunks, and tasks for testing."""
    # Create first plan with tasks
    assert cli.main(["new", "--root", str(root), "plan", "Alpha Project"]) == 0
    assert cli.main(["new", "--root", str(root), "chunk", "PLAN-001", "Backend API"]) == 0
    assert cli.main(["new", "--root", str(root), "task", "CHUNK-001", "Add schema", "--complexity", "medium"]) == 0
    assert cli.main(["new", "--root", str(root), "task", "CHUNK-001", "Add validation", "--complexity", "low"]) == 0

    # Create second plan for project filtering tests
    assert cli.main(["new", "--root", str(root), "plan", "Beta Project", "--project", "beta"]) == 0
    assert cli.main(["new", "--root", str(root), "chunk", "PLAN-002", "Frontend UI"]) == 0
    assert cli.main(["new", "--root", str(root), "task", "CHUNK-002", "Add component"]) == 0


def test_md_flag_produces_markdown_no_ansi(tmp_path: Path, capsys):
    """Verify --md outputs markdown without ANSI escape codes."""
    _init_workspace(tmp_path)
    _create_test_artifacts(tmp_path)
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path), "--md"])
    out = capsys.readouterr().out

    assert code == 0
    # Check for absence of ANSI escape codes
    assert "\033[" not in out, "Output contains ANSI escape sequences"
    assert "\x1b[" not in out, "Output contains ANSI escape sequences"


def test_md_has_valid_structure(tmp_path: Path, capsys):
    """Verify markdown output has proper headers and table structure."""
    _init_workspace(tmp_path)
    _create_test_artifacts(tmp_path)
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path), "--md"])
    out = capsys.readouterr().out

    assert code == 0

    # Check for main header
    assert "# Onward Report" in out

    # Check for all required section headers
    assert "## Complexity Remaining" in out
    assert "## In Progress" in out
    assert "## Upcoming" in out
    assert "## Next" in out
    assert "## Blocking Human Tasks" in out
    assert "## Recent Completed" in out
    assert "## Active Work Tree" in out

    # Check for table separators (markdown table format)
    assert "|---|" in out or "|---" in out

    # Check for metadata
    assert "**Generated:**" in out


def test_md_with_project_filter(tmp_path: Path, capsys):
    """Verify --md works correctly with --project filtering."""
    _init_workspace(tmp_path)
    _create_test_artifacts(tmp_path)
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path), "--md", "--project", "beta"])
    out = capsys.readouterr().out

    assert code == 0
    assert "# Onward Report" in out
    assert "**Project:** beta" in out

    # Should include beta project artifacts
    assert "Beta Project" in out or "PLAN-002" in out

    # Should NOT include alpha project artifacts in filtered output
    # (Note: "Alpha" might appear in headers/structure, so we check for specific tasks)
    assert "PLAN-001" not in out or "Alpha Project" not in out


def test_md_with_verbose_includes_run_stats(tmp_path: Path, capsys):
    """Verify --md --verbose includes Run Stats section."""
    _init_workspace(tmp_path)
    _create_test_artifacts(tmp_path)
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path), "--md", "--verbose"])
    out = capsys.readouterr().out

    assert code == 0
    assert "## Run Stats" in out
    # Run stats should have a table
    assert "| Metric | Value |" in out or any(
        line.strip().startswith("| Total runs") for line in out.splitlines()
    )


def test_md_without_verbose_no_run_stats(tmp_path: Path, capsys):
    """Verify --md without --verbose does not include Run Stats."""
    _init_workspace(tmp_path)
    _create_test_artifacts(tmp_path)
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path), "--md"])
    out = capsys.readouterr().out

    assert code == 0
    assert "## Run Stats" not in out


def test_md_with_no_color_does_not_error(tmp_path: Path, capsys):
    """Verify --md and --no-color flags are orthogonal and don't conflict."""
    _init_workspace(tmp_path)
    _create_test_artifacts(tmp_path)
    capsys.readouterr()

    # Should not error when both flags are used
    code = cli.main(["report", "--root", str(tmp_path), "--md", "--no-color"])
    out = capsys.readouterr().out

    assert code == 0
    assert "# Onward Report" in out
    assert "\033[" not in out


def test_default_report_without_md_unchanged(tmp_path: Path, capsys):
    """Verify default report (without --md) still works as before."""
    _init_workspace(tmp_path)
    _create_test_artifacts(tmp_path)
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path)])
    out = capsys.readouterr().out

    assert code == 0
    # Default report should have its traditional format
    assert "== Onward Report ==" in out
    # Should NOT be markdown
    assert "# Onward Report" not in out


def test_md_empty_sections_show_none(tmp_path: Path, capsys):
    """Verify empty sections display as *None* in markdown."""
    _init_workspace(tmp_path)
    # Don't create any artifacts - workspace is empty
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path), "--md"])
    out = capsys.readouterr().out

    assert code == 0
    # Empty sections should show italic None
    assert "*None*" in out


def test_md_tables_have_proper_format(tmp_path: Path, capsys):
    """Verify markdown tables have header rows and separator rows."""
    _init_workspace(tmp_path)
    _create_test_artifacts(tmp_path)
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path), "--md"])
    out = capsys.readouterr().out

    assert code == 0

    # Complexity Remaining table
    assert "| low | medium | high | unestimated |" in out

    # Check for table separators (all tables should have these)
    separator_pattern = re.compile(r'\|[-]+\|')
    matches = separator_pattern.findall(out)
    assert len(matches) > 0, "No table separators found"


def test_md_active_work_tree_as_code_block(tmp_path: Path, capsys):
    """Verify Active Work Tree is rendered as a fenced code block."""
    _init_workspace(tmp_path)
    _create_test_artifacts(tmp_path)
    capsys.readouterr()

    code = cli.main(["report", "--root", str(tmp_path), "--md"])
    out = capsys.readouterr().out

    assert code == 0

    # Find the Active Work Tree section
    lines = out.splitlines()
    tree_idx = None
    for i, line in enumerate(lines):
        if "## Active Work Tree" in line:
            tree_idx = i
            break

    assert tree_idx is not None, "Active Work Tree section not found"

    # Check for code fence after the header (allowing for empty line)
    found_fence = False
    for i in range(tree_idx + 1, min(tree_idx + 5, len(lines))):
        if lines[i].strip() == "```":
            found_fence = True
            break

    # Either should have code fence (if there's content) or *None* (if empty)
    assert found_fence or any("*None*" in lines[i] for i in range(tree_idx + 1, min(tree_idx + 5, len(lines))))


def test_md_output_is_pipeable(tmp_path: Path):
    """Verify markdown output can be captured and written to a file."""
    _init_workspace(tmp_path)
    _create_test_artifacts(tmp_path)

    # Capture output
    import sys
    from io import StringIO

    old_stdout = sys.stdout
    sys.stdout = captured = StringIO()

    try:
        code = cli.main(["report", "--root", str(tmp_path), "--md"])
        output = captured.getvalue()
    finally:
        sys.stdout = old_stdout

    assert code == 0
    assert len(output) > 0

    # Write to file and verify it's readable markdown
    md_file = tmp_path / "report.md"
    md_file.write_text(output, encoding="utf-8")

    content = md_file.read_text(encoding="utf-8")
    assert "# Onward Report" in content
    assert "\033[" not in content
