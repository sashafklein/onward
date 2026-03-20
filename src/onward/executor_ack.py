"""Machine-readable task success acknowledgments from executor stdout/stderr."""

from __future__ import annotations

import json
from typing import Any

# Bump when the acknowledgment object shape changes incompatibly.
SUCCESS_ACK_SCHEMA_VERSION = 1


def _validate_ack_object(obj: dict[str, Any], expected_run_id: str) -> tuple[bool, str]:
    otr = obj.get("onward_task_result")
    if not isinstance(otr, dict):
        return False, "onward_task_result must be an object"

    ver = otr.get("schema_version", 1)
    if ver != SUCCESS_ACK_SCHEMA_VERSION:
        return False, f"onward_task_result.schema_version must be {SUCCESS_ACK_SCHEMA_VERSION} (got {ver!r})"

    status = str(otr.get("status", "")).lower().strip()
    if status != "completed":
        return False, "onward_task_result.status must be 'completed' for a successful task run"

    rid = otr.get("run_id")
    if rid is not None and str(rid).strip() != "" and str(rid) != expected_run_id:
        return (
            False,
            f"onward_task_result.run_id mismatch (expected {expected_run_id!r}, got {rid!r})",
        )
    return True, ""


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
