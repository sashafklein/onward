from __future__ import annotations

from pathlib import Path

DEFAULT_DIRECTORIES = [
    ".onward/plans",
    ".onward/plans/.archive",
    ".onward/templates",
    ".onward/prompts",
    ".onward/hooks",
    ".onward/sync",
    ".onward/runs",
    ".onward/reviews",
    ".onward/notes",
]

DEFAULT_FILES = {
    ".onward.config.yaml": """# Onward workspace config.
# This file is read by the CLI at runtime. Keep it in repo root.

# Schema version for future migrations.
version: 1

# Artifact directories (.onward/, etc.) are fixed relative to the workspace root.

sync:
  # Sync mode: local (disabled), branch (same repo branch), repo (separate repo).
  mode: local
  # Branch name used when sync mode is "branch".
  branch: onward
  # Optional separate git repository URL/path used when mode is "repo".
  repo: null
  # Local worktree path used for sync staging operations.
  worktree_path: .onward/sync

ralph:
  # Executor command to run for `onward work`, markdown hooks, and `review-plan`.
  command: ralph
  # Default arguments appended to the executor command.
  args: []
  # When false, the CLI still runs shell hooks but does not invoke the executor.
  enabled: true

models:
  # Fallback model for generic operations when no more specific model is set.
  # Supports aliases: opus-latest, sonnet-latest, codex-latest, haiku-latest.
  default: opus-latest
  # Default model for newly created tasks.
  task_default: sonnet-latest
  # Default model used by `onward split` decomposition (blank = use default).
  split_default:
  # Default model for review-oriented hooks/workflows.
  review_default: codex-latest

review:
  # If true, plan reviews spawn two independent reviewers (review_default + default).
  double_review: true

work:
  # If true (default), `onward work CHUNK` runs every ready task in one invocation.
  # If false, each invocation runs at most one ready task; re-run until the chunk finishes.
  sequential_by_default: true

hooks:
  # Shell commands run before each task (empty list means disabled).
  pre_task_shell: []
  # Shell commands run after each task (empty list means disabled).
  post_task_shell: []
  # Optional markdown hook path executed before each task (null disables).
  pre_task_markdown: null
  # Optional markdown hook path executed after each task.
  post_task_markdown: .onward/hooks/post-task.md
  # Optional markdown hook path executed after chunk completion.
  post_chunk_markdown: .onward/hooks/post-chunk.md
""",
    ".onward/templates/plan.md": """# Summary

<!-- For a semi-technical layperson: What does this scope of work accomplish? 2-4 sentences, not in the weeds. -->

# Problem

<!-- Optional -->

# Goals

<!-- Bullets -->

# Non-goals

<!-- Bullets -->

# End state

<!-- A checklist of user stories representing the ideal end state. -->

# Context

<!-- Optional -->

# Proposed approach

<!-- This section could be huge. As big as it needs to. Hundreds of lines. The goal is to exhaustively specify the plan. Everything we intend to do. Files, tests, connections, etc. -->

# Key artifacts

<!-- Optional. If relevant, any ENVs, processes, etc that may need to be documented or acted on when the work is complete. -->

# Acceptance criteria

<!-- Specific tests, e2es, QA assertions, file existences, documentation, etc, that attest to the successful completion of the work -->

# Notes

<!-- Optional -->
""",
    ".onward/templates/chunk.md": """# Summary

<!-- For a semi-technical layperson: what this chunk ships and why it matters. -->

# Scope

<!-- Concrete bullets of what is in this chunk. -->

# Out of scope

<!-- Concrete bullets of what is explicitly not included. -->

# Dependencies

<!-- IDs, systems, or decisions that must exist first. -->

# Expected files/systems involved

<!-- List likely files, directories, services, and tables touched. -->

# Completion criteria

<!-- Checklist that can be verified by tests/review. -->

# Notes

<!-- Optional -->
""",
    ".onward/templates/task.md": """# Context

<!-- What this task is doing and where it fits in the chunk. -->

# Scope

<!-- Tight, concrete bullets. Keep this task small and finishable. -->

# Out of scope

<!-- Explicitly exclude adjacent work. -->

# Files to inspect

<!-- Start here. Include exact paths when known. -->

# Implementation notes

<!-- Constraints, gotchas, and edge cases to handle. -->

# Acceptance criteria

<!-- Binary checks: tests, outputs, behavior changes, docs updates. -->

# Handoff notes

<!-- What the parent/next worker should know. Include follow-up ideas if discovered. -->
""",
    ".onward/templates/run.md": """# Execution summary

<!-- Short narrative of what was attempted and result. -->

# Inputs

<!-- Task ID, model/executor, important context passed in. -->

# Output

<!-- Key output, files changed, and notable terminal/log details. -->

# Follow-up

<!-- Blockers, refactors, or for-later tasks discovered during execution. -->
""",
    ".onward/prompts/split-plan.md": """You are decomposing a plan into executable chunks.

Output strict JSON with this exact shape:
{
  "chunks": [
    {
      "title": "string",
      "description": "string",
      "priority": "low|medium|high",
      "model": "string"
    }
  ]
}

Constraints:
- Return at least one chunk.
- Keep chunk titles short and concrete.
- Do not include markdown fences or any non-JSON text.
""",
    ".onward/prompts/split-chunk.md": """You are decomposing a chunk into executable tasks.

Output strict JSON with this exact shape:
{
  "tasks": [
    {
      "title": "string",
      "description": "string",
      "acceptance": ["string"],
      "model": "string",
      "human": false
    }
  ]
}

Constraints:
- Return at least one task.
- Each task must include one or more acceptance checks.
- Do not include markdown fences or any non-JSON text.
""",
    ".onward/prompts/review-plan.md": """You are an adversarial plan reviewer. Your job is to find gaps, risks, and issues that the plan author missed. Be thorough and direct.

Review the plan for:
- **Gaps in requirements:** Are there missing edge cases, undefined behaviors, or unstated assumptions?
- **Security implications:** Does the plan introduce attack surface, handle sensitive data, or need auth/authz considerations?
- **Deployment and operational risks:** Are there migration concerns, rollback strategies, monitoring needs, or ENV/config changes not addressed?
- **Scope concerns:** Is the plan trying to do too much? Too little? Are boundaries clear?
- **Feasibility:** Are there technical risks, unproven approaches, or dependency concerns?
- **Testing strategy:** Is the testing plan adequate? Are there gaps in coverage?

Rate each finding by severity:
- **Critical:** Must be addressed before work begins. Security holes, data loss risks, fundamental design flaws.
- **Important:** Should be addressed. Missing requirements, deployment gaps, significant edge cases.
- **Minor:** Nice to fix. Code quality, documentation, minor edge cases.
- **Nitpick:** Optional. Style preferences, suggestions, alternative approaches.

Output your review in this exact markdown format:

## Review: {plan title}

### Overall Assessment: {Approved | Revision Needed | Blocked}

### Findings

| # | Severity | Category | Finding | Recommendation |
|---|----------|----------|---------|----------------|
| 1 | Critical | ... | ... | ... |

If there are no findings at a given severity, omit those rows. If the plan is genuinely solid, say so — but that should be rare.

### Notes

Any broader observations about the approach, architecture, or patterns that don't fit neatly into the findings table.
""",
    ".onward/hooks/post-task.md": """---
id: HOOK-post-task
type: hook
trigger: task.completed
model: opus-latest
executor: ralph
scope: repo
---

# Purpose
Summarize what changed and propose next tasks.

# Inputs
- Completed task
- Run output

# Instructions
1. Confirm acceptance criteria status.
2. Note key files touched.
3. Propose follow-up tasks if needed.

# Required output
- Short completion summary
- Follow-up list (if any)
""",
    ".onward/hooks/post-chunk.md": """---
id: HOOK-post-chunk
type: hook
trigger: chunk.completed
model: opus-latest
executor: ralph
scope: repo
---

# Purpose
Capture chunk-level completion and recommend plan updates.

# Inputs
- Completed chunk
- Child task outcomes

# Instructions
1. Verify the chunk completion criteria.
2. Summarize major outputs and known risks.
3. Suggest next chunk ordering.

# Required output
- Chunk completion status
- Risks and recommended next actions
""",
    ".onward/plans/index.yaml": """generated_at: null
plans: []
chunks: []
tasks: []
runs: []
""",
    ".onward/plans/recent.yaml": """generated_at: null
completed: []
""",
    ".onward/ongoing.json": """{
  "version": 1,
  "updated_at": null,
  "active_runs": []
}
""",
}

GITIGNORE_LINES = [
    ".onward/plans/.archive/",
    ".onward/sync/",
    ".onward/runs/",
    ".onward/reviews/",
    ".onward/ongoing.json",
    ".dogfood/",
]

REQUIRED_PATHS = [
    ".onward.config.yaml",
    ".onward/templates/plan.md",
    ".onward/templates/chunk.md",
    ".onward/templates/task.md",
    ".onward/templates/run.md",
    ".onward/prompts/split-plan.md",
    ".onward/prompts/split-chunk.md",
    ".onward/plans/index.yaml",
    ".onward/plans/recent.yaml",
]


def write_workspace_file(path: Path, content: str, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def update_gitignore(root: Path) -> bool:
    gitignore = root / ".gitignore"
    existing = []
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8").splitlines()

    changed = False
    lines = existing.copy()
    for entry in GITIGNORE_LINES:
        if entry not in lines:
            lines.append(entry)
            changed = True

    if not changed:
        return False

    gitignore.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def _is_workspace_root(root: Path) -> bool:
    return (
        (root / ".onward.config.yaml").exists()
        and (root / ".onward").exists()
        and (root / ".onward/plans").exists()
    )


def require_workspace(root: Path) -> None:
    if _is_workspace_root(root):
        return
    raise ValueError(
        f"not an Onward workspace: {root}. Run `onward init` here (or pass --root <workspace>)"
    )
