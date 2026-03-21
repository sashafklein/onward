from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode, ScalarNode


class _ArtifactDumper(yaml.SafeDumper):
    """YAML dumper tuned for Onward artifacts: plain mapping keys, double-quoted string scalars."""

    def represent_mapping(self, tag: str, mapping: Any, flow_style: bool | None = None) -> yaml.Node:
        """Like SafeRepresenter.represent_mapping, but simple string keys stay plain (not quoted)."""
        value: list[tuple[yaml.Node, yaml.Node]] = []
        node = MappingNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        if hasattr(mapping, "items"):
            mapping = list(mapping.items())
            if self.sort_keys:
                try:
                    mapping = sorted(mapping)
                except TypeError:
                    pass
        for item_key, item_value in mapping:
            if isinstance(item_key, str) and re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", item_key):
                node_key = self.represent_scalar("tag:yaml.org,2002:str", item_key)
            else:
                node_key = self.represent_data(item_key)
            node_value = self.represent_data(item_value)
            if not (isinstance(node_key, ScalarNode) and not node_key.style):
                best_style = False
            if not (isinstance(node_value, ScalarNode) and not node_value.style):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node


def _represent_str_quoted(dumper: yaml.Dumper, data: str) -> yaml.Node:
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')


_ArtifactDumper.add_representer(str, _represent_str_quoted)


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_timestamp() -> str:
    return _now_iso().replace(":", "-")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "item"


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_priority(value: Any) -> str:
    priority = _clean_string(value).lower()
    return priority if priority in {"low", "medium", "high"} else "medium"


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _clean_string(value).lower() in {"1", "true", "yes", "y"}


def _normalize_acceptance(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    single = _clean_string(value)
    return [single] if single else []


def _normalize_effort(value: Any) -> str:
    raw = _clean_string(str(value)).lower()
    return raw if raw in {"xs", "s", "m", "l", "xl"} else ""


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [raw]


def _colorize(text: str, color: str, enabled: bool) -> str:
    if not enabled:
        return text
    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "bold": "\033[1m",
    }
    reset = "\033[0m"
    return f"{colors.get(color, '')}{text}{reset}" if color in colors else text


def _status_color(status: str) -> str:
    return {
        "open": "yellow",
        "in_progress": "blue",
        "completed": "green",
        "canceled": "magenta",
        "failed": "red",
    }.get(status, "cyan")


# ---------------------------------------------------------------------------
# YAML (PyYAML)
# ---------------------------------------------------------------------------


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty yaml")
    try:
        loaded = yaml.safe_load(stripped)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid yaml: {exc}") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError("yaml root must be a mapping")
    return loaded


def _dump_simple_yaml(data: dict[str, Any]) -> str:
    dumped = yaml.dump(
        data,
        Dumper=_ArtifactDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=4096,
        indent=2,
    )
    if not dumped.endswith("\n"):
        dumped += "\n"
    return dumped


# Older run snapshots may omit keys Onward now writes; readers merge these defaults (real values win).
_RUN_RECORD_OPTIONAL_DEFAULTS: dict[str, Any] = {
    "type": "run",
    "plan": None,
    "chunk": None,
    "executor": "onward-exec",
    "error": "",
    "finished_at": None,
}


def _normalize_run_record_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Fill optional run-record keys missing in pre-unification snapshots."""
    return {**_RUN_RECORD_OPTIONAL_DEFAULTS, **data}


def _dump_run_json_record(data: dict[str, Any]) -> str:
    """Serialize a task run snapshot for `.onward/runs/RUN-*.json` (strict JSON, UTF-8)."""
    return json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def _read_run_json_record(text: str) -> dict[str, Any]:
    """Parse `.onward/runs/RUN-*.json`. Accepts JSON or legacy simple-YAML-shaped content."""
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty run record")
    try:
        loaded = json.loads(stripped)
    except json.JSONDecodeError:
        loaded = _parse_simple_yaml(stripped)
    if not isinstance(loaded, dict):
        raise ValueError("run record root must be a mapping")
    return _normalize_run_record_dict(loaded)


def _split_frontmatter(raw: str) -> tuple[str | None, str]:
    if not raw.startswith("---\n"):
        return None, raw
    remainder = raw[4:]
    marker = "\n---\n"
    idx = remainder.find(marker)
    if idx < 0:
        return None, raw
    frontmatter = remainder[:idx]
    body = remainder[idx + len(marker) :]
    return frontmatter, body


def _markdown_section(body: str, heading: str) -> str:
    target = heading.strip().lower()
    lines = body.splitlines()
    start = -1
    for i, line in enumerate(lines):
        match = re.match(r"^#{1,6}\s+(.*)$", line.strip())
        if not match:
            continue
        if match.group(1).strip().lower() == target:
            start = i + 1
            break
    if start < 0:
        return ""
    end = len(lines)
    for i in range(start, len(lines)):
        if re.match(r"^#{1,6}\s+", lines[i].strip()):
            end = i
            break
    return "\n".join(lines[start:end]).strip()


def _extract_markdown_list_items(section: str) -> list[str]:
    items: list[str] = []
    for line in section.splitlines():
        match = re.match(r"^\s*(?:-|\d+\.)\s+(.+?)\s*$", line)
        if match:
            value = match.group(1).strip()
            if value:
                items.append(value)
    return items


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _get_head_sha(root: Path) -> str:
    """Return current HEAD commit SHA, or empty string when git is unavailable or has no commits."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    return ""


def _compute_files_changed(root: Path, before_sha: str) -> list[str]:
    """Return list of files changed between ``before_sha`` and HEAD.

    Falls back to an empty list when ``before_sha`` is empty, git is
    unavailable, or the diff command fails.
    """
    if not before_sha:
        return []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", before_sha, "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# Stable public names for cross-module use (PLAN-010 TASK-012).
# ---------------------------------------------------------------------------

clean_string = _clean_string
normalize_bool = _normalize_bool
parse_simple_yaml = _parse_simple_yaml
colorize = _colorize
dump_simple_yaml = _dump_simple_yaml
now_iso = _now_iso
slugify = _slugify
split_frontmatter = _split_frontmatter
status_color = _status_color
as_str_list = _as_str_list
dump_run_json_record = _dump_run_json_record
read_run_json_record = _read_run_json_record
run_timestamp = _run_timestamp
extract_markdown_list_items = _extract_markdown_list_items
markdown_section = _markdown_section
normalize_acceptance = _normalize_acceptance
normalize_priority = _normalize_priority
normalize_effort = _normalize_effort
get_head_sha = _get_head_sha
compute_files_changed = _compute_files_changed
