from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any


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
    }.get(status, "cyan")


# ---------------------------------------------------------------------------
# Custom YAML parser / dumper (no PyYAML dependency)
# ---------------------------------------------------------------------------


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value in {"null", "~"}:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def _read_dash_sequence(lines: list[str], j: int, min_indent: int) -> tuple[list[Any], int]:
    """Read ``- item`` lines strictly deeper than ``min_indent`` (list under a key)."""
    seq: list[Any] = []
    while j < len(lines):
        row = lines[j]
        if not row.strip():
            j += 1
            continue
        ri = len(row) - len(row.lstrip())
        if ri <= min_indent:
            break
        ls = row.lstrip()
        if not ls.startswith("- "):
            break
        frag = ls[2:].strip()
        entry_indent = ri
        if ":" in frag:
            sk, sv = frag.split(":", 1)
            sk, sv = sk.strip(), sv.strip()
            entry: dict[str, Any] = {sk: (_parse_scalar(sv) if sv else "")}
            j += 1
            if not sv:
                while j < len(lines):
                    r2 = lines[j]
                    if not r2.strip():
                        j += 1
                        continue
                    r2i = len(r2) - len(r2.lstrip())
                    if r2i <= entry_indent:
                        break
                    if r2.lstrip().startswith("- "):
                        break
                    if ":" not in r2.strip():
                        break
                    tk, tv = r2.strip().split(":", 1)
                    entry[tk.strip()] = _parse_scalar(tv.strip()) if tv.strip() else ""
                    j += 1
            else:
                while j < len(lines):
                    r2 = lines[j]
                    if not r2.strip():
                        j += 1
                        continue
                    r2i = len(r2) - len(r2.lstrip())
                    if r2i <= entry_indent:
                        break
                    if r2.lstrip().startswith("- "):
                        break
                    if ":" not in r2.strip():
                        break
                    tk, tv = r2.strip().split(":", 1)
                    if not tv.strip():
                        break
                    entry[tk.strip()] = _parse_scalar(tv.strip())
                    j += 1
            seq.append(entry)
            continue
        seq.append(_parse_scalar(frag))
        j += 1
    return seq, j


def _mapping_yaml_list_item(lines: list[str], j: int) -> tuple[dict[str, Any], int]:
    """Parse one ``  - key: val`` mapping item and optional ``    more:`` / nested lists."""
    line = lines[j]
    if not line.startswith("  -"):
        raise ValueError(f"expected indented list item: {line!r}")
    rest = line[4:].strip() if line.startswith("  - ") else line[3:].strip()
    if not rest or ":" not in rest:
        raise ValueError(f"expected mapping list item (key: value): {line!r}")
    k, v = rest.split(":", 1)
    k, v = k.strip(), v.strip()
    obj: dict[str, Any] = {}
    j += 1
    if not v:
        seq, j = _read_dash_sequence(lines, j, min_indent=3)
        obj[k] = seq
        return obj, j
    obj[k] = _parse_scalar(v)
    while j < len(lines):
        row = lines[j]
        if not row.strip():
            j += 1
            continue
        ri = len(row) - len(row.lstrip())
        if ri < 4:
            break
        if ri == 2 and row.lstrip().startswith("-"):
            break
        inner = row.strip()
        if ":" not in inner:
            raise ValueError(f"expected key: value, got {row!r}")
        nk, nv = inner.split(":", 1)
        nk, nv = nk.strip(), nv.strip()
        if not nv:
            seq, j = _read_dash_sequence(lines, j + 1, min_indent=ri)
            obj[nk] = seq
            continue
        obj[nk] = _parse_scalar(nv)
        j += 1
    return obj, j


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    i = 0
    result: dict[str, Any] = {}

    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue

        if line.startswith("  "):
            raise ValueError(f"unexpected indentation near: {line}")

        if ":" not in line:
            raise ValueError(f"invalid yaml line: {line}")

        key, remainder = line.split(":", 1)
        key = key.strip()
        remainder = remainder.strip()

        if remainder:
            result[key] = _parse_scalar(remainder)
            i += 1
            continue

        j = i + 1
        list_items: list[Any] = []
        nested_lines: list[str] = []

        while j < len(lines):
            child = lines[j]
            if not child.strip():
                j += 1
                continue
            if not child.startswith("  "):
                break

            if child.startswith("  - "):
                tail = child[4:].strip()
                if ":" in tail:
                    item, j = _mapping_yaml_list_item(lines, j)
                    list_items.append(item)
                    continue
                list_items.append(_parse_scalar(tail))
                j += 1
                continue
            nested_lines.append(child[2:])
            j += 1

        if list_items and nested_lines:
            raise ValueError(f"mixed nested yaml not supported for key: {key}")

        if list_items:
            result[key] = list_items
        elif nested_lines:
            result[key] = _parse_simple_yaml("\n".join(nested_lines))
        else:
            result[key] = ""

        i = j

    return result


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def _dump_simple_yaml_lines(data: Any, indent: int = 0) -> list[str]:
    pad = " " * indent

    if isinstance(data, dict):
        out: list[str] = []
        for key, value in data.items():
            if isinstance(value, dict):
                if not value:
                    out.append(f"{pad}{key}: {{}}")
                    continue
                out.append(f"{pad}{key}:")
                out.extend(_dump_simple_yaml_lines(value, indent + 2))
            elif isinstance(value, list):
                if not value:
                    out.append(f"{pad}{key}: []")
                    continue
                out.append(f"{pad}{key}:")
                out.extend(_dump_simple_yaml_lines(value, indent + 2))
            else:
                out.append(f"{pad}{key}: {_format_scalar(value)}")
        return out

    if isinstance(data, list):
        out = []
        for item in data:
            if isinstance(item, (dict, list)):
                out.append(f"{pad}-")
                out.extend(_dump_simple_yaml_lines(item, indent + 2))
            else:
                out.append(f"{pad}- {_format_scalar(item)}")
        return out

    return [f"{pad}{_format_scalar(data)}"]


def _dump_simple_yaml(data: dict[str, Any]) -> str:
    return "\n".join(_dump_simple_yaml_lines(data)) + "\n"


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
