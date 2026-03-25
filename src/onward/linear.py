"""Linear GraphQL API client for syncing Onward plans to Linear issues."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LINEAR_API_URL = "https://api.linear.app/graphql"

LAST_PULL_FILENAME = "linear_last_pull"


class LinearError(Exception):
    """Raised when a Linear API call fails."""


@dataclass(frozen=True)
class WorkflowState:
    id: str
    name: str
    category: str  # backlog, unstarted, started, completed, canceled


@dataclass(frozen=True)
class LinearIssue:
    id: str
    identifier: str  # e.g. "ENG-42"
    title: str
    url: str


@dataclass(frozen=True)
class LinearIssueFull:
    """Rich issue data returned by fetch_team_issues."""
    id: str
    identifier: str
    title: str
    url: str
    priority: int  # 0=none, 1=urgent, 2=high, 3=medium, 4=low
    sort_order: float
    state_category: str  # backlog, unstarted, started, completed, canceled
    description: str
    updated_at: str  # ISO timestamp from Linear


def get_api_key() -> str | None:
    return os.environ.get("LINEAR_API_KEY", "").strip() or None


def get_team_id(config: dict[str, Any]) -> str | None:
    linear = config.get("linear")
    if not isinstance(linear, dict):
        return None
    tid = linear.get("team_id")
    if tid is None:
        return None
    return str(tid).strip() or None


def get_stale_after(config: dict[str, Any]) -> int:
    """Return linear.stale_after in minutes (0 = always pull). Previously poll_interval."""
    linear = config.get("linear")
    if not isinstance(linear, dict):
        return 0
    raw = linear.get("stale_after")
    if raw is None:
        raw = linear.get("poll_interval")  # backward compat
    if raw is None:
        return 0
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def is_linear_configured(config: dict[str, Any]) -> bool:
    return get_team_id(config) is not None and get_api_key() is not None


def read_last_pull_time(artifact_root: Path) -> datetime | None:
    path = artifact_root / LAST_PULL_FILENAME
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
        return datetime.fromisoformat(text)
    except (ValueError, OSError):
        return None


def write_last_pull_time(artifact_root: Path) -> None:
    path = artifact_root / LAST_PULL_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")


def should_auto_pull(config: dict[str, Any], artifact_root: Path) -> bool:
    """True if Linear is configured and stale_after minutes have elapsed since last pull."""
    if not is_linear_configured(config):
        return False
    stale = get_stale_after(config)
    last = read_last_pull_time(artifact_root)
    if last is None:
        return True
    if stale == 0:
        return True
    elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 60
    return elapsed >= stale


def _graphql(query: str, variables: dict[str, Any] | None, api_key: str) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        LINEAR_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode()[:500]
        except Exception:
            pass
        raise LinearError(f"Linear API returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise LinearError(f"Linear API request failed: {exc.reason}") from exc

    if "errors" in data and data["errors"]:
        msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
        raise LinearError(f"Linear GraphQL errors: {msgs}")
    return data.get("data", {})


_TEAM_STATES_QUERY = """
query TeamStates($teamId: String!) {
  team(id: $teamId) {
    states {
      nodes {
        id
        name
        type
      }
    }
  }
}
"""


def fetch_team_states(api_key: str, team_id: str) -> list[WorkflowState]:
    data = _graphql(_TEAM_STATES_QUERY, {"teamId": team_id}, api_key)
    team = data.get("team")
    if not team:
        raise LinearError(f"Team {team_id!r} not found (check linear.team_id in config)")
    nodes = team.get("states", {}).get("nodes", [])
    return [
        WorkflowState(id=n["id"], name=n["name"], category=n.get("type", ""))
        for n in nodes
        if isinstance(n, dict) and "id" in n and "name" in n
    ]


# Maps Onward status → Linear workflow state category.
# Linear categories: backlog, unstarted, started, completed, canceled, triage
_STATUS_TO_CATEGORY: dict[str, str] = {
    "open": "unstarted",
    "in_progress": "started",
    "completed": "completed",
    "canceled": "canceled",
    "failed": "unstarted",
}


def map_status_to_state(onward_status: str, states: list[WorkflowState]) -> WorkflowState | None:
    category = _STATUS_TO_CATEGORY.get(onward_status, "unstarted")
    for s in states:
        if s.category == category:
            return s
    return states[0] if states else None


_CREATE_ISSUE_MUTATION = """
mutation CreateIssue($teamId: String!, $title: String!, $description: String, $stateId: String) {
  issueCreate(input: {teamId: $teamId, title: $title, description: $description, stateId: $stateId}) {
    success
    issue {
      id
      identifier
      title
      url
    }
  }
}
"""


def create_issue(
    api_key: str,
    team_id: str,
    title: str,
    description: str | None = None,
    state_id: str | None = None,
) -> LinearIssue:
    variables: dict[str, Any] = {"teamId": team_id, "title": title}
    if description:
        variables["description"] = description
    if state_id:
        variables["stateId"] = state_id
    data = _graphql(_CREATE_ISSUE_MUTATION, variables, api_key)
    result = data.get("issueCreate", {})
    if not result.get("success"):
        raise LinearError("issueCreate returned success=false")
    issue = result.get("issue", {})
    return LinearIssue(
        id=issue["id"],
        identifier=issue["identifier"],
        title=issue["title"],
        url=issue.get("url", ""),
    )


_UPDATE_ISSUE_MUTATION = """
mutation UpdateIssue($issueId: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $issueId, input: $input) {
    success
  }
}
"""


def update_issue(
    api_key: str,
    issue_id: str,
    *,
    state_id: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> bool:
    """Update one or more fields on a Linear issue."""
    input_fields: dict[str, Any] = {}
    if state_id is not None:
        input_fields["stateId"] = state_id
    if title is not None:
        input_fields["title"] = title
    if description is not None:
        input_fields["description"] = description
    if not input_fields:
        return True
    data = _graphql(_UPDATE_ISSUE_MUTATION, {"issueId": issue_id, "input": input_fields}, api_key)
    return bool(data.get("issueUpdate", {}).get("success"))


def update_issue_state(api_key: str, issue_id: str, state_id: str) -> bool:
    """Backward-compatible wrapper."""
    return update_issue(api_key, issue_id, state_id=state_id)


_GET_ISSUE_QUERY = """
query GetIssue($issueId: String!) {
  issue(id: $issueId) {
    id
    identifier
    title
    description
    url
    state {
      id
      name
      type
    }
  }
}
"""


def get_issue(api_key: str, issue_id: str) -> dict[str, Any] | None:
    """Fetch a single issue by ID. Returns raw dict or None if not found."""
    try:
        data = _graphql(_GET_ISSUE_QUERY, {"issueId": issue_id}, api_key)
    except LinearError:
        return None
    return data.get("issue")


# ---------------------------------------------------------------------------
# Fetch team issues (for linear pull)
# ---------------------------------------------------------------------------

_TEAM_ISSUES_QUERY = """
query TeamIssues($teamId: String!, $after: String) {
  team(id: $teamId) {
    issues(
      first: 100
      after: $after
      filter: { state: { type: { nin: ["completed", "canceled"] } } }
    ) {
      nodes {
        id
        identifier
        title
        url
        priority
        sortOrder
        description
        updatedAt
        state {
          type
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""


def fetch_team_issues(api_key: str, team_id: str) -> list[LinearIssueFull]:
    """Fetch all non-archived/non-completed issues for a team, paginated."""
    issues: list[LinearIssueFull] = []
    cursor: str | None = None
    while True:
        variables: dict[str, Any] = {"teamId": team_id}
        if cursor:
            variables["after"] = cursor
        data = _graphql(_TEAM_ISSUES_QUERY, variables, api_key)
        team = data.get("team")
        if not team:
            raise LinearError(f"Team {team_id!r} not found")
        issues_data = team.get("issues", {})
        for n in issues_data.get("nodes", []):
            if not isinstance(n, dict) or "id" not in n:
                continue
            issues.append(LinearIssueFull(
                id=n["id"],
                identifier=n.get("identifier", ""),
                title=n.get("title", ""),
                url=n.get("url", ""),
                priority=int(n.get("priority", 0)),
                sort_order=float(n.get("sortOrder", 0)),
                state_category=n.get("state", {}).get("type", ""),
                description=n.get("description", "") or "",
                updated_at=n.get("updatedAt", ""),
            ))
        page_info = issues_data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
    # Sort by sort_order (board position) — canonical prioritisation.
    issues.sort(key=lambda i: i.sort_order)
    return issues


# Linear priority int → Onward priority string
# 0=none, 1=urgent, 2=high, 3=medium, 4=low
_LINEAR_PRIORITY_TO_ONWARD: dict[int, str] = {
    0: "medium",  # unprioritized → default medium
    1: "high",    # urgent → high
    2: "high",    # high → high
    3: "medium",  # medium → medium
    4: "low",     # low → low
}

# Onward status from Linear state category
_CATEGORY_TO_STATUS: dict[str, str] = {
    "backlog": "open",
    "triage": "open",
    "unstarted": "open",
    "started": "in_progress",
    "completed": "completed",
    "canceled": "canceled",
}


def linear_priority_to_onward(priority: int) -> str:
    return _LINEAR_PRIORITY_TO_ONWARD.get(priority, "medium")


def linear_category_to_status(category: str) -> str:
    return _CATEGORY_TO_STATUS.get(category, "open")
