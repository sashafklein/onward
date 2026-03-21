from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def make_default_layout(workspace_root: Path):
    """Create a WorkspaceLayout with default .onward root for testing.

    This helper allows tests to use the new WorkspaceLayout API without
    needing to change test behavior. It creates a layout equivalent to
    the default configuration (no root/roots specified in config).

    Args:
        workspace_root: Path to the workspace root directory

    Returns:
        WorkspaceLayout instance with .onward as the artifact root
    """
    from onward.config import WorkspaceLayout
    return WorkspaceLayout.from_config(workspace_root, {})
