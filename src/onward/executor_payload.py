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


def with_schema_version(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the executor stdin payload with `schema_version` set."""
    out = dict(payload)
    out["schema_version"] = EXECUTOR_PAYLOAD_SCHEMA_VERSION
    return out


def validate_executor_stdin_payload(payload: dict[str, Any]) -> list[str]:
    """Best-effort validation for tests and tooling; returns human-readable issues."""
    issues: list[str] = []
    ver = payload.get("schema_version")
    if ver != EXECUTOR_PAYLOAD_SCHEMA_VERSION:
        issues.append(f"schema_version must be {EXECUTOR_PAYLOAD_SCHEMA_VERSION} (got {ver!r})")

    ptype = str(payload.get("type", ""))
    if ptype == "task":
        missing = sorted(_TASK_REQUIRED - set(payload))
        if missing:
            issues.append(f"task payload missing keys: {', '.join(missing)}")
    elif ptype == "review":
        missing = sorted(_REVIEW_REQUIRED - set(payload))
        if missing:
            issues.append(f"review payload missing keys: {', '.join(missing)}")
    elif ptype == "hook":
        missing_common = sorted(_HOOK_COMMON - set(payload))
        if missing_common:
            issues.append(f"hook payload missing keys: {', '.join(missing_common)}")
        phase = str(payload.get("phase", ""))
        if phase == "post_chunk_markdown":
            missing = sorted(_HOOK_CHUNK_EXTRA - set(payload))
            if missing:
                issues.append(f"post_chunk hook payload missing keys: {', '.join(missing)}")
        else:
            missing = sorted(_HOOK_TASK_EXTRA - set(payload))
            if missing:
                issues.append(f"task hook payload missing keys: {', '.join(missing)}")
    else:
        issues.append(f"unknown or missing payload type {ptype!r}")

    return issues
