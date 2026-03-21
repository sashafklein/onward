from __future__ import annotations

from typing import Any

# Bump when stdin JSON shape changes incompatibly for executors.
EXECUTOR_PAYLOAD_SCHEMA_VERSION = 1

_TASK_REQUIRED = frozenset({
    "type",
    "schema_version",
    "run_id",
    "task",
    "body",
    "notes",
    "notes_hint",
    "chunk",
    "plan",
})

_REVIEW_REQUIRED = frozenset({
    "type",
    "schema_version",
    "model",
    "plan_id",
    "prompt",
    "plan_metadata",
    "plan_body",
})

_HOOK_COMMON = frozenset({"type", "schema_version", "phase", "model", "hook_path", "hook_body"})

_HOOK_TASK_EXTRA = frozenset({"run_id", "task", "task_body"})
_HOOK_CHUNK_EXTRA = frozenset({"chunk", "chunk_body"})

_SPLIT_REQUIRED = frozenset({
    "type",
    "schema_version",
    "model",
    "prompt",
    "artifact_metadata",
    "artifact_body",
    "split_type",
})


def with_schema_version(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the executor stdin payload with `schema_version` set."""
    out = dict(payload)
    out["schema_version"] = EXECUTOR_PAYLOAD_SCHEMA_VERSION
    return out


def normalize_executor_stdin_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Copy payload; set ``schema_version`` if absent or null (legacy captures before versioning)."""
    out = dict(payload)
    if "schema_version" not in out or out["schema_version"] is None:
        out["schema_version"] = EXECUTOR_PAYLOAD_SCHEMA_VERSION
    return out


def validate_executor_stdin_payload(payload: dict[str, Any]) -> list[str]:
    """Best-effort validation for tests and tooling; returns human-readable issues.

    Payloads without ``schema_version`` are treated as legacy pre-contract stdin and validated
    against the current shape after implicit version defaulting.
    """
    issues: list[str] = []
    ver = payload.get("schema_version")
    has_version_key = "schema_version" in payload
    if has_version_key and ver is not None and ver != EXECUTOR_PAYLOAD_SCHEMA_VERSION:
        issues.append(f"schema_version must be {EXECUTOR_PAYLOAD_SCHEMA_VERSION} (got {ver!r})")

    effective = normalize_executor_stdin_payload(payload)

    ptype = str(effective.get("type", ""))
    if ptype == "task":
        missing = sorted(_TASK_REQUIRED - set(effective))
        if missing:
            issues.append(f"task payload missing keys: {', '.join(missing)}")
    elif ptype == "review":
        missing = sorted(_REVIEW_REQUIRED - set(effective))
        if missing:
            issues.append(f"review payload missing keys: {', '.join(missing)}")
    elif ptype == "hook":
        missing_common = sorted(_HOOK_COMMON - set(effective))
        if missing_common:
            issues.append(f"hook payload missing keys: {', '.join(missing_common)}")
        phase = str(effective.get("phase", ""))
        if phase == "post_chunk_markdown":
            missing = sorted(_HOOK_CHUNK_EXTRA - set(effective))
            if missing:
                issues.append(f"post_chunk hook payload missing keys: {', '.join(missing)}")
        else:
            missing = sorted(_HOOK_TASK_EXTRA - set(effective))
            if missing:
                issues.append(f"task hook payload missing keys: {', '.join(missing)}")
    elif ptype == "split":
        missing = sorted(_SPLIT_REQUIRED - set(effective))
        if missing:
            issues.append(f"split payload missing keys: {', '.join(missing)}")
    else:
        issues.append(f"unknown or missing payload type {ptype!r}")

    return issues
