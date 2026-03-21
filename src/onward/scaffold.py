from __future__ import annotations

from pathlib import Path


def default_directories(artifact_root: str) -> list[str]:
    """Return the list of artifact directories relative to workspace root."""
    return [
        f"{artifact_root}/plans",
        f"{artifact_root}/plans/.archive",
        f"{artifact_root}/templates",
        f"{artifact_root}/prompts",
        f"{artifact_root}/hooks",
        f"{artifact_root}/sync",
        f"{artifact_root}/runs",
        f"{artifact_root}/reviews",
        f"{artifact_root}/notes",
    ]


# Backward-compatible constant
DEFAULT_DIRECTORIES = default_directories(".onward")


def default_files(artifact_root: str) -> dict[str, str]:
    """Return the dict of default files with paths relative to workspace root."""
    return {
        ".onward.config.yaml": f"""# Onward workspace config.
# This file is read by the CLI at runtime. Keep it in repo root.

# Schema version for future migrations.
version: 1

# Artifact root directory (default: .onward)
# Uncomment to use a non-hidden directory (e.g., for Obsidian sync):
# root: .onward
#
# Multi-root workspaces (separate artifact trees per project):
# roots:
#   frontend: .fe-plans
#   backend: .be-plans
# default_project: frontend

# Artifact directories ({artifact_root}/, etc.) are fixed relative to the workspace root.

sync:
  # Sync mode: local (disabled), branch (same repo branch), repo (separate repo).
  mode: local
  # Branch name used when sync mode is "branch".
  branch: onward
  # Optional separate git repository URL/path used when mode is "repo".
  repo: null
  # Local worktree path used for sync staging operations.
  worktree_path: {artifact_root}/sync

executor:
  # Executor command for `onward work`, markdown hooks, and `review-plan`.
  # "builtin" (or blank) runs Claude/Cursor CLIs directly with streamed output.
  # Set to a custom command (e.g. "onward-exec") for the JSON stdin subprocess protocol.
  command: builtin
  # Default arguments appended to the executor command.
  args: []
  # When false, the CLI still runs shell hooks but does not invoke the executor.
  enabled: true

models:
  # Ultimate fallback and baseline tier (required logically; empty uses opus).
  default: opus
  # Tiered defaults with automatic fallbacks (null/blank walks the chain — see docs/CAPABILITIES.md).
  high: opus
  medium: sonnet
  low: haiku
  # Split decomposition; blank falls back through split -> default.
  split:
  # Plan review slots; blank falls back review_1/review_2 -> high -> default.
  review_1: codex
  review_2:

review:
  # If true, plan reviews spawn two independent reviewers (review_1 + review_2 tiers).
  double_review: true
  # Optional: explicit reviewer slots with ordered fallbacks (see docs/CAPABILITIES.md).
  # When review.reviewers is a non-empty list, double_review is ignored for slot count.

work:
  # If true (default), `onward work CHUNK` runs every ready task in one invocation.
  # If false, each invocation runs at most one ready task; re-run until the chunk finishes.
  sequential_by_default: true
  # When true, exit code 0 is not enough: the executor must print a JSON success ack line
  # (see docs/WORK_HANDOFF.md). Default false for backward compatibility.
  require_success_ack: false
  # Refuse `onward work` when the task's run_count reaches this (after failed runs). 0 = unlimited.
  max_retries: 3

hooks:
  # Shell commands run before each task (empty list means disabled).
  pre_task_shell: []
  # Shell commands once when `onward work CHUNK-*` starts, before any task in that chunk.
  pre_chunk_shell: []
  # Shell commands run after each task (ONWARD_* env vars are set — see docs/WORK_HANDOFF.md).
  post_task_shell:
    - "git add -A && git commit -m 'onward: completed ${{ONWARD_TASK_ID}} - ${{ONWARD_TASK_TITLE}}' --allow-empty"
  # Optional markdown hook path executed after each successful task (executor-backed).
  post_task_markdown: {artifact_root}/hooks/post-task.md
  # Optional markdown hook path executed after chunk completion (executor-backed).
  post_chunk_markdown: {artifact_root}/hooks/post-chunk.md
""",
        f"{artifact_root}/templates/plan.md": """# Summary

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
        f"{artifact_root}/templates/chunk.md": """# Summary

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

<!-- Optional. Frontmatter may include optional ``complexity: low|medium|high`` and ``estimated_files: <int>`` for chunks. -->
""",
        f"{artifact_root}/templates/task.md": """# Context

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

<!-- Frontmatter may include optional ``complexity: low|medium|high``. -->
""",
        f"{artifact_root}/templates/run.md": """# Execution summary

<!-- Short narrative of what was attempted and result. -->

# Inputs

<!-- Task ID, model/executor, important context passed in. -->

# Output

<!-- Key output, files changed, and notable terminal/log details. -->

# Follow-up

<!-- Blockers, refactors, or for-later tasks discovered during execution. -->
""",
        f"{artifact_root}/prompts/split-plan.md": """You decompose a **plan** into **chunks** of work. Each chunk is a coherent slice that can be executed and tested on its own. Follow the sizing and structure rules below.

## Sizing and scope

- Target **20–30 files touched** per chunk (count likely edits across the repo: source, tests, docs, config). If the codebase is small, prefer fewer, deeper chunks rather than many tiny ones.
- Prefer **3–8 chunks** for a typical plan; merge or split if you are far outside that range.
- Each chunk must have **clear boundaries**: what it delivers, what it explicitly does not do, and how we know it is done.

## File touch map

For every chunk, estimate which paths are involved using three buckets (repo-relative paths or globs):

- **must**: files or directories that will definitely change.
- **likely**: files that will probably change or need inspection.
- **deferred**: follow-ups or optional paths explicitly not in this chunk.

If you are unsure of paths, use coarse entries (e.g. src/onward/) rather than omitting the map.

## Dependencies between chunks

- Output **depends_on_index**: a JSON array of **0-based indices** into your chunks array pointing to chunks that must complete before this one.
- Only reference earlier or independent chunks; never create cycles. A chunk must not depend on a later index.
- Use an empty array when the chunk has no chunk-level dependencies.

## Acceptance and testing

- **acceptance**: an array of **binary, checkable** criteria (tests pass, command succeeds, behavior X observable). Avoid vague wording.

## Priority and model

- **priority**: low, medium, or high (default medium).
- **model**: suggest an executor model alias for work in this chunk (haiku, sonnet, opus, etc.).

## Output format

Output a single JSON object (no markdown code fences, no prose outside JSON). Required top-level key: chunks (non-empty array).

Each element of chunks must include: title (string), description (string), priority (low|medium|high), model (string), depends_on_index (array of integers), files (object with keys must, likely, deferred — each an array of strings), acceptance (array of strings).

Illustrative minimal object (structure only):

{"chunks":[{"title":"A","description":"...","priority":"medium","model":"sonnet","depends_on_index":[],"files":{"must":[],"likely":[],"deferred":[]},"acceptance":["checkable criterion"]}]}

Rules: Return at least one chunk. Keep titles short and concrete. JSON only on stdout.
""",
        f"{artifact_root}/prompts/split-chunk.md": """You decompose a **chunk** into **tasks** small enough for one focused execution pass. Each task must be self-contained: an implementer can finish it using only this task's title, description, acceptance, and file list—without hunting the parent plan for missing context.

## Sizing

- Target **≤6 files** touched per task (repo-relative paths). If a task would exceed that, split it.
- If you must list **7–9 files**, flag it in the file list but prefer splitting.
- More than **9 files** in one task is unacceptable—split into multiple tasks.

## Self-containment

- **description** must state what to do and where, with enough concrete detail that "see the plan" is never required.
- **files** must list the paths you expect to read or edit (array of strings). Use [] only when truly unknown; prefer best guesses.
- **acceptance** must be binary and verifiable (tests, CLI output, behavior).

## Models and complexity

- **model**: haiku for trivial edits; sonnet for typical work; opus for deep refactors or cross-cutting design.
- **complexity**: low | medium | high — rough size (optional but preferred).

## Ordering within the chunk

- **depends_on_index**: 0-based indices into your tasks array for tasks that must finish before this one. No cycles. Empty array if none.

## Output format

Output a single JSON object (no markdown code fences, no prose outside JSON). Required top-level key: tasks (non-empty array).

Each element of tasks must include: title (string), description (string), acceptance (array of strings), model (string), human (boolean), depends_on_index (array of integers), files (array of strings), complexity (string: low|medium|high or empty string if unknown).

Illustrative minimal object (structure only):

{"tasks":[{"title":"Add helper","description":"Implement X in src/foo.py","acceptance":["tests pass"],"model":"sonnet","human":false,"depends_on_index":[],"files":["src/foo.py"],"complexity":"medium"}]}

Rules: Return at least one task. Each task needs at least one acceptance criterion. JSON only on stdout.
""",
        f"{artifact_root}/prompts/review-plan.md": """You are an adversarial plan reviewer. Your job is to find gaps, risks, and issues that the plan author missed. Be thorough and direct.

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
        f"{artifact_root}/hooks/post-task.md": """---
id: HOOK-post-task
type: hook
trigger: task.completed
model: opus
executor: onward-exec
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
        f"{artifact_root}/hooks/post-chunk.md": """---
id: HOOK-post-chunk
type: hook
trigger: chunk.completed
model: opus
executor: onward-exec
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
        f"{artifact_root}/plans/index.yaml": """generated_at: null
index_version: 1
plans: []
chunks: []
tasks: []
runs: []
""",
        f"{artifact_root}/plans/recent.yaml": """generated_at: null
completed: []
""",
        f"{artifact_root}/ongoing.json": """{
  "version": 1,
  "updated_at": null,
  "active_runs": []
}
""",
    }


# Backward-compatible constant
DEFAULT_FILES = default_files(".onward")


def gitignore_lines(artifact_root: str) -> list[str]:
    """Return the list of gitignore entries for the artifact root."""
    return [
        f"{artifact_root}/plans/.archive/",
        f"{artifact_root}/sync/",
        f"{artifact_root}/runs/",
        f"{artifact_root}/reviews/",
        f"{artifact_root}/ongoing.json",
        ".dogfood/",
    ]


# Backward-compatible constant
GITIGNORE_LINES = gitignore_lines(".onward")


def required_paths(artifact_root: str) -> list[str]:
    """Return the list of required paths for validation."""
    return [
        ".onward.config.yaml",
        f"{artifact_root}/templates/plan.md",
        f"{artifact_root}/templates/chunk.md",
        f"{artifact_root}/templates/task.md",
        f"{artifact_root}/templates/run.md",
        f"{artifact_root}/prompts/split-plan.md",
        f"{artifact_root}/prompts/split-chunk.md",
        f"{artifact_root}/plans/index.yaml",
        f"{artifact_root}/plans/recent.yaml",
    ]


# Backward-compatible constant
REQUIRED_PATHS = required_paths(".onward")


def write_workspace_file(path: Path, content: str, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def update_gitignore(root: Path, artifact_root: str = ".onward") -> bool:
    """Update .gitignore with artifact root entries.

    Args:
        root: Workspace root directory
        artifact_root: Artifact root path (default: ".onward")

    Returns:
        True if .gitignore was modified, False otherwise
    """
    gitignore = root / ".gitignore"
    existing = []
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8").splitlines()

    changed = False
    lines = existing.copy()
    for entry in gitignore_lines(artifact_root):
        if entry not in lines:
            lines.append(entry)
            changed = True

    if not changed:
        return False

    gitignore.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def _is_workspace_root(root: Path, artifact_root: str = ".onward") -> bool:
    """Check if a directory is a valid Onward workspace root.

    Args:
        root: Workspace root directory
        artifact_root: Artifact root path (default: ".onward")

    Returns:
        True if the directory appears to be a valid workspace
    """
    config_path = root / ".onward.config.yaml"
    if not config_path.exists():
        # Legacy: check default .onward/plans
        return (root / artifact_root / "plans").exists()
    
    # Config exists — check configured roots
    from onward.util import parse_simple_yaml
    config = parse_simple_yaml(config_path.read_text(encoding="utf-8")) or {}
    
    config_root = config.get("root")
    config_roots = config.get("roots")
    
    # Multi-root mode: check if at least one configured root has plans/
    if config_roots and isinstance(config_roots, dict):
        for path_str in config_roots.values():
            if not path_str:
                continue
            path = Path(path_str)
            if not path.is_absolute():
                path = root / path
            if (path / "plans").exists():
                return True
        return False
    
    # Single custom root mode
    if config_root:
        root_str = str(config_root).strip()
        if root_str:
            custom_path = Path(root_str)
            if not custom_path.is_absolute():
                custom_path = root / custom_path
            return (custom_path / "plans").exists()
    
    # Default mode
    return (root / artifact_root / "plans").exists()


def require_workspace(root: Path, artifact_root: str = ".onward") -> None:
    """Require that a directory is a valid Onward workspace.

    Args:
        root: Workspace root directory
        artifact_root: Artifact root path (default: ".onward")

    Raises:
        ValueError: If the directory is not a valid workspace
    """
    if _is_workspace_root(root, artifact_root):
        return
    raise ValueError(
        f"not an Onward workspace: {root}. Run `onward init` here (or pass --root <workspace>)"
    )
