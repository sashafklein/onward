import pytest

from onward import cli
from onward.util import _dump_simple_yaml, _parse_simple_yaml, _split_frontmatter


def test_parse_simple_yaml_round_trip_lists_and_scalars():
    frontmatter = """id: TASK-001
type: task
depends_on:
  - TASK-010
  - TASK-011
blocked_by: []
files:
  - src/a.py
  - src/b.py
enabled: true
count: 3
ratio: 1.5
notes: null
"""

    parsed = _parse_simple_yaml(frontmatter)
    assert parsed["depends_on"] == ["TASK-010", "TASK-011"]
    assert parsed["blocked_by"] == []
    assert parsed["enabled"] is True
    assert parsed["count"] == 3
    assert parsed["ratio"] == 1.5
    assert parsed["notes"] is None

    dumped = _dump_simple_yaml(parsed)
    reparsed = _parse_simple_yaml(dumped)

    assert reparsed == parsed


def test_parse_simple_yaml_rejects_mixed_nested_block():
    invalid = """key:
  - item
  nested: value
"""

    with pytest.raises(ValueError, match="mixed nested yaml"):
        _parse_simple_yaml(invalid)


def test_split_frontmatter_parses_body():
    raw = """---
id: TASK-001
type: task
---

# Body\n"""

    frontmatter, body = _split_frontmatter(raw)

    assert "id: TASK-001" in frontmatter
    assert body.startswith("\n# Body")


def test_split_frontmatter_without_markers_returns_none():
    frontmatter, body = _split_frontmatter("# no frontmatter")
    assert frontmatter is None
    assert body == "# no frontmatter"
