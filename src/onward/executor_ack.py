"""Machine-readable task success acknowledgments from executor stdout/stderr."""

from __future__ import annotations

import json
from typing import Any

# Current acknowledgment schema version emitted by tooling; v1 and v2 remain accepted.
SUCCESS_ACK_SCHEMA_VERSION = 3


def _coerce_schema_version(raw: Any) -> int | None:
    if raw is None:
        return 1
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip(), 10)
    return None


def _validate_v2_optional_fields(otr: dict[str, Any]) -> str:
    if "files_changed" in otr and otr["files_changed"] is not None:
        if not isinstance(otr["files_changed"], list):
            return "onward_task_result.files_changed must be a list"
        for i, p in enumerate(otr["files_changed"]):
            if not isinstance(p, str):
                return f"onward_task_result.files_changed[{i}] must be a string"
    if "follow_ups" in otr and otr["follow_ups"] is not None:
        if not isinstance(otr["follow_ups"], list):
            return "onward_task_result.follow_ups must be a list"
        for i, item in enumerate(otr["follow_ups"]):
            if not isinstance(item, dict):
                return f"onward_task_result.follow_ups[{i}] must be an object"
    for key in ("acceptance_met", "acceptance_unmet"):
        if key in otr and otr[key] is not None:
            if not isinstance(otr[key], list):
                return f"onward_task_result.{key} must be a list"
            for i, item in enumerate(otr[key]):
                if not isinstance(item, str):
                    return f"onward_task_result.{key}[{i}] must be a string"
    if "summary" in otr and otr["summary"] is not None and not isinstance(otr["summary"], str):
        return "onward_task_result.summary must be a string"
    if "notes" in otr and otr["notes"] is not None and not isinstance(otr["notes"], str):
        return "onward_task_result.notes must be a string"
    return ""


def _validate_ack_object(obj: dict[str, Any], expected_run_id: str) -> tuple[bool, str]:
    otr = obj.get("onward_task_result")
    if not isinstance(otr, dict):
        return False, "onward_task_result must be an object"

    ver = _coerce_schema_version(otr.get("schema_version", 1))
    if ver is None or ver not in (1, 2, 3):
        return False, f"onward_task_result.schema_version must be 1, 2, or 3 (got {otr.get('schema_version')!r})"

    status = str(otr.get("status", "")).lower().strip()
    if status != "completed":
        return False, "onward_task_result.status must be 'completed' for a successful task run"

    rid = otr.get("run_id")
    if rid is not None and str(rid).strip() != "" and str(rid) != expected_run_id:
        return (
            False,
            f"onward_task_result.run_id mismatch (expected {expected_run_id!r}, got {rid!r})",
        )

    if ver in (2, 3):
        err = _validate_v2_optional_fields(otr)
        if err:
            return False, err

    return True, ""


def parse_task_result(obj: dict[str, Any]) -> dict[str, Any]:
    """Normalize ``onward_task_result`` fields for storage and display (v1, v2, and v3)."""
    otr = obj.get("onward_task_result")
    if not isinstance(otr, dict):
        return _empty_normalized_result()

    ver = _coerce_schema_version(otr.get("schema_version", 1))
    if ver is None or ver not in (1, 2, 3):
        ver = 1

    summary = ""
    if otr.get("summary") is not None:
        summary = str(otr.get("summary", "") or "")
    notes = ""
    if otr.get("notes") is not None:
        notes = str(otr.get("notes", "") or "")

    files_changed: list[str] = []
    raw_fc = otr.get("files_changed")
    if isinstance(raw_fc, list):
        files_changed = [str(x).strip() for x in raw_fc if str(x).strip()]

    follow_ups: list[dict[str, str]] = []
    raw_fu = otr.get("follow_ups")
    if isinstance(raw_fu, list):
        for item in raw_fu:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            desc = str(item.get("description", "")).strip()
            if not title or not desc:
                continue
            pri = str(item.get("priority", "medium")).strip().lower()
            if pri not in {"low", "medium", "high"}:
                pri = "medium"
            follow_ups.append({"title": title, "description": desc, "priority": pri})

    def _acc(key: str) -> list[str]:
        raw = otr.get(key)
        if not isinstance(raw, list):
            return []
        return [str(x).strip() for x in raw if str(x).strip()]

    rid_s = ""
    if otr.get("run_id") is not None:
        rid_s = str(otr.get("run_id")).strip()

    token_usage: dict[str, Any] | None = None
    raw_tu = otr.get("token_usage")
    if isinstance(raw_tu, dict):
        token_usage = raw_tu

    return {
        "schema_version": ver,
        "status": str(otr.get("status", "")).lower().strip(),
        "run_id": rid_s,
        "summary": summary,
        "files_changed": files_changed,
        "follow_ups": follow_ups,
        "acceptance_met": _acc("acceptance_met"),
        "acceptance_unmet": _acc("acceptance_unmet"),
        "notes": notes,
        "token_usage": token_usage,
    }


def _empty_normalized_result() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "",
        "run_id": "",
        "summary": "",
        "files_changed": [],
        "follow_ups": [],
        "acceptance_met": [],
        "acceptance_unmet": [],
        "notes": "",
        "token_usage": None,
    }


def _scan_text_for_ack(text: str, expected_run_id: str) -> tuple[bool, str, dict[str, Any] | None]:
    """Bottom-up: first JSON object line containing ``onward_task_result`` wins."""
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or "onward_task_result" not in obj:
            continue
        valid, err = _validate_ack_object(obj, expected_run_id)
        if valid:
            return True, "", obj
        return False, err, None
    return False, "", None


def find_task_success_ack(
    stdout: str,
    stderr: str,
    expected_run_id: str,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Locate a valid success acknowledgment (scan stdout, then stderr, bottom-up).

    Returns ``(found, error_message, evidence)`` where ``evidence`` is the parsed JSON
    object (including the ``onward_task_result`` wrapper) when ``found`` is true.
    """
    for text, label in ((stdout, "stdout"), (stderr, "stderr")):
        found, err, obj = _scan_text_for_ack(text, expected_run_id)
        if found:
            return True, "", obj
        if err:
            return False, f"{label}: {err}", None

    return (
        False,
        "missing onward_task_result line with status \"completed\" "
        "(enable work.require_success_ack only after your executor prints this JSON; "
        "see docs/WORK_HANDOFF.md)",
        None,
    )
