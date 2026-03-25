"""Linear GraphQL API client for syncing Onward plans to Linear issues."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

LINEAR_API_URL = "https://api.linear.app/graphql"


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
mutation UpdateIssue($issueId: String!, $stateId: String!) {
  issueUpdate(id: $issueId, input: {stateId: $stateId}) {
    success
  }
}
"""


def update_issue_state(api_key: str, issue_id: str, state_id: str) -> bool:
    data = _graphql(_UPDATE_ISSUE_MUTATION, {"issueId": issue_id, "stateId": state_id}, api_key)
    return bool(data.get("issueUpdate", {}).get("success"))


_GET_ISSUE_QUERY = """
query GetIssue($issueId: String!) {
  issue(id: $issueId) {
    id
    identifier
    title
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
