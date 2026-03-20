from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onward.artifacts import regenerate_indexes
from onward.config import clean_string, load_workspace_config


@dataclass(frozen=True)
class SyncSettings:
    mode: str
    branch: str
    repo: str
    worktree_rel: str


def _sync_section(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("sync")
    if isinstance(raw, dict):
        return raw
    return {}


def parse_sync_settings(config: dict[str, Any]) -> SyncSettings:
    sec = _sync_section(config)
    mode = clean_string(sec.get("mode", "local")).lower() or "local"
    if mode not in {"local", "branch", "repo"}:
        mode = "local"
    branch = clean_string(sec.get("branch", "onward"))
    repo_val = sec.get("repo")
    repo = ""
    if repo_val is not None and str(repo_val).strip().lower() not in {"", "null", "none", "~"}:
        repo = str(repo_val).strip()
    worktree_rel = clean_string(sec.get("worktree_path", ".onward/sync")) or ".onward/sync"
    return SyncSettings(mode=mode, branch=branch, repo=repo, worktree_rel=worktree_rel)


def validate_sync_config(root: Path, config: dict[str, Any]) -> list[str]:
    """Return human-readable issues for doctor (empty if OK)."""
    sec = _sync_section(config)
    if not sec:
        return []

    issues: list[str] = []
    mode_raw = clean_string(sec.get("mode", "local")).lower() or "local"
    if mode_raw not in {"local", "branch", "repo"}:
        issues.append(f"sync.mode must be local, branch, or repo (got {mode_raw!r})")

    settings = parse_sync_settings(config)

    if settings.mode == "branch":
        if not settings.branch:
            issues.append('sync.branch is required when sync.mode is "branch"')
        if not settings.worktree_rel:
            issues.append("sync.worktree_path must be set for branch sync")
        if not (root / ".git").exists():
            issues.append("sync.mode is branch but this directory is not a git repository (.git missing)")

    if settings.mode == "repo":
        if not settings.repo:
            issues.append('sync.repo is required when sync.mode is "repo" (remote URL or path)')
        if not settings.worktree_rel:
            issues.append("sync.worktree_path must be set for repo sync")

    return issues


def plans_dir(root: Path) -> Path:
    return root / ".onward" / "plans"


def _worktree_abs(root: Path, settings: SyncSettings) -> Path:
    path = Path(settings.worktree_rel)
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def _git(cmd: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *cmd],
        cwd=str(cwd),
        check=check,
        capture_output=True,
        text=True,
    )


def _inside_git_repo(root: Path) -> bool:
    return (root / ".git").exists()


def _remove_if_empty_dir(path: Path) -> None:
    if path.is_dir() and not any(path.iterdir()):
        path.rmdir()


def ensure_branch_worktree(root: Path, settings: SyncSettings) -> Path:
    if settings.mode != "branch":
        raise ValueError("internal: ensure_branch_worktree in non-branch mode")
    if not _inside_git_repo(root):
        raise ValueError("branch sync requires a git repository at the workspace root")

    wt = _worktree_abs(root, settings)
    git_file = wt / ".git"

    if wt.exists() and not git_file.exists():
        if wt.is_dir() and not any(wt.iterdir()):
            wt.rmdir()
        else:
            raise ValueError(
                f"sync worktree path {wt} exists but is not a git worktree "
                f"(remove it or pick another sync.worktree_path)"
            )

    if git_file.exists():
        return wt

    parent = wt.parent
    parent.mkdir(parents=True, exist_ok=True)
    _remove_if_empty_dir(wt)

    # Does branch exist?
    show = _git(["show-ref", "--verify", f"refs/heads/{settings.branch}"], root, check=False)
    if show.returncode == 0:
        proc = _git(["worktree", "add", str(wt), settings.branch], root, check=False)
    else:
        proc = _git(["worktree", "add", "-b", settings.branch, str(wt), "HEAD"], root, check=False)

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise ValueError(f"git worktree add failed: {err}")

    plans = wt / ".onward" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    return wt


def ensure_repo_clone(root: Path, settings: SyncSettings) -> Path:
    if settings.mode != "repo":
        raise ValueError("internal: ensure_repo_clone in non-repo mode")

    wt = _worktree_abs(root, settings)
    git_dir = wt / ".git"

    if git_dir.exists():
        return wt

    wt.parent.mkdir(parents=True, exist_ok=True)
    if wt.exists():
        if wt.is_dir() and not any(wt.iterdir()):
            wt.rmdir()
        else:
            raise ValueError(
                f"sync worktree path {wt} exists but is not a git clone "
                f"(remove it or pick another sync.worktree_path)"
            )

    proc = _git(["clone", settings.repo, str(wt)], root, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise ValueError(f"git clone failed: {err}")

    plans = wt / ".onward" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    return wt


def remote_plans_path(root: Path, settings: SyncSettings) -> Path:
    if settings.mode == "branch":
        wt = ensure_branch_worktree(root, settings)
    elif settings.mode == "repo":
        wt = ensure_repo_clone(root, settings)
    else:
        raise ValueError("remote plans requested in local mode")
    return wt / ".onward" / "plans"


def _remote_plans_path_if_ready(root: Path, settings: SyncSettings) -> Path | None:
    """Return remote plans dir only if sync checkout already exists (no clone/worktree side effects)."""
    if settings.mode not in {"branch", "repo"}:
        return None
    wt = _worktree_abs(root, settings)
    if not (wt / ".git").exists():
        return None
    return wt / ".onward" / "plans"


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def plans_snapshot(plans_root: Path) -> dict[str, str]:
    """Relative path -> sha256 for regular files under plans_root."""
    if not plans_root.exists():
        return {}
    out: dict[str, str] = {}
    for p in sorted(plans_root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(plans_root).as_posix()
            if rel.startswith(".git/"):
                continue
            out[rel] = _file_digest(p)
    return out


def compare_plans(local_root: Path, remote_root: Path) -> tuple[bool, list[str]]:
    """Return (in_sync, human messages for differences)."""
    a = plans_snapshot(local_root)
    b = plans_snapshot(remote_root)
    keys = sorted(set(a) | set(b))
    messages: list[str] = []
    for k in keys:
        if k not in a:
            messages.append(f"only on remote: {k}")
        elif k not in b:
            messages.append(f"only locally: {k}")
        elif a[k] != b[k]:
            messages.append(f"differ: {k}")
    return (len(messages) == 0, messages)


def mirror_plans(src: Path, dst: Path) -> None:
    """Make dst mirror src (files only; dirs created as needed)."""
    if not src.exists():
        raise ValueError(f"source plans directory missing: {src}")

    dst.mkdir(parents=True, exist_ok=True)

    src_files: set[str] = set()
    for p in src.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(src).as_posix()
        if rel.startswith(".git/"):
            continue
        src_files.add(rel)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)

    # Remove files in dst that are not in src (keep directory structure minimal)
    for p in list(dst.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(dst).as_posix()
        if rel not in src_files:
            p.unlink()

    # Prune empty dirs (deepest first)
    for p in sorted((d for d in dst.rglob("*") if d.is_dir()), key=lambda x: len(x.parts), reverse=True):
        try:
            if not any(p.iterdir()):
                p.rmdir()
        except OSError:
            pass


def git_commit_plans_if_changed(wt: Path, message: str) -> bool:
    _git(["add", "-A", ".onward/plans"], wt, check=True)
    st = _git(["status", "--porcelain", "--", ".onward/plans"], wt, check=True)
    if not st.stdout.strip():
        return False
    _git(["commit", "-m", message], wt, check=True)
    return True


def git_push(wt: Path) -> None:
    proc = _git(["push", "-u", "origin", "HEAD"], wt, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise ValueError(
            f"git push failed: {err}\n"
            "Configure a remote in the sync worktree or push manually from that checkout."
        )


def git_pull_ff_only(wt: Path) -> None:
    proc = _git(["pull", "--ff-only"], wt, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise ValueError(
            f"git pull --ff-only failed: {err}\n"
            "Resolve conflicts in the sync worktree, then run `onward sync pull` again."
        )


def cmd_sync_status(root: Path) -> tuple[int, list[str]]:
    config = load_workspace_config(root)
    settings = parse_sync_settings(config)
    lines: list[str] = []
    local = plans_dir(root)

    if settings.mode == "local":
        lines.append(f"Sync mode: local (no remote target). Plans: {local.relative_to(root)}")
        lines.append("Local vs remote: n/a")
        return 0, lines

    remote_plans = _remote_plans_path_if_ready(root, settings)
    if remote_plans is None:
        lines.append(f"Sync mode: {settings.mode}")
        lines.append(f"Local plans: {local.relative_to(root)}")
        lines.append("Remote sync checkout: not initialized (run `onward sync push` once)")
        lines.append("Status: unknown until the sync target exists")
        return 0, lines

    in_sync, diffs = compare_plans(local, remote_plans)
    rel_remote = remote_plans.relative_to(root) if remote_plans.is_relative_to(root) else remote_plans
    lines.append(f"Sync mode: {settings.mode}")
    lines.append(f"Local plans:  {local.relative_to(root)}")
    lines.append(f"Remote plans: {rel_remote}")
    if in_sync:
        lines.append("Status: clean (local and remote plans match)")
    else:
        lines.append("Status: dirty")
        for d in diffs[:50]:
            lines.append(f"  - {d}")
        if len(diffs) > 50:
            lines.append(f"  ... and {len(diffs) - 50} more")
    return 0, lines


def cmd_sync_push(root: Path) -> tuple[int, list[str]]:
    config = load_workspace_config(root)
    settings = parse_sync_settings(config)
    if settings.mode == "local":
        return 1, ["sync push skipped: sync.mode is local. Set sync.mode to branch or repo in .onward.config.yaml"]

    local = plans_dir(root)
    lines: list[str] = []

    try:
        if settings.mode == "branch":
            wt = ensure_branch_worktree(root, settings)
        else:
            wt = ensure_repo_clone(root, settings)
        remote_plans = wt / ".onward" / "plans"
    except ValueError as exc:
        return 1, [str(exc)]

    mirror_plans(local, remote_plans)
    lines.append(f"Copied local plans -> {remote_plans}")

    committed = git_commit_plans_if_changed(wt, "onward sync push")
    lines.append("Committed changes in sync worktree" if committed else "No commit (no plan changes)")

    try:
        git_push(wt)
        lines.append("Pushed to remote")
    except ValueError as exc:
        lines.append(str(exc))
        # Partial success: files copied and maybe committed
        return 1, lines

    return 0, lines


def cmd_sync_pull(root: Path) -> tuple[int, list[str]]:
    config = load_workspace_config(root)
    settings = parse_sync_settings(config)
    if settings.mode == "local":
        return 1, ["sync pull skipped: sync.mode is local. Set sync.mode to branch or repo in .onward.config.yaml"]

    local = plans_dir(root)
    lines: list[str] = []

    try:
        if settings.mode == "branch":
            wt = ensure_branch_worktree(root, settings)
        else:
            wt = ensure_repo_clone(root, settings)
        remote_plans = wt / ".onward" / "plans"
    except ValueError as exc:
        return 1, [str(exc)]

    try:
        git_pull_ff_only(wt)
        lines.append("Fast-forwarded sync worktree from remote")
    except ValueError as exc:
        return 1, [str(exc)]

    mirror_plans(remote_plans, local)
    lines.append(f"Copied remote plans -> {local.relative_to(root)}")
    regenerate_indexes(root)
    lines.append("Regenerated plan indexes")
    return 0, lines
