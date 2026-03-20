from __future__ import annotations

from pathlib import Path
from typing import Any

from onward.util import clean_string, normalize_bool, parse_simple_yaml

MODEL_FAMILIES: dict[str, str] = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4",
    "codex": "codex-5-3",
    "gpt5": "gpt-5",
}

# Declared keys for `.onward.config.yaml` (unknown keys fail `onward doctor`).
CONFIG_TOP_LEVEL_KEYS = frozenset({"version", "sync", "ralph", "models", "review", "work", "hooks"})

CONFIG_SECTION_KEYS: dict[str, frozenset[str]] = {
    "sync": frozenset({"mode", "branch", "repo", "worktree_path"}),
    "ralph": frozenset({"command", "args", "enabled"}),
    "models": frozenset({"default", "task_default", "split_default", "review_default"}),
    "review": frozenset({"double_review"}),
    "work": frozenset({"sequential_by_default"}),
    "hooks": frozenset({
        "pre_task_shell",
        "post_task_shell",
        "pre_task_markdown",
        "post_task_markdown",
        "post_chunk_markdown",
    }),
}

_REMOVED_WORK_KEYS = frozenset({"create_worktree", "worktree_root", "base_branch"})


def _repo_value_set(repo_val: Any) -> bool:
    if repo_val is None:
        return False
    return clean_string(str(repo_val)).lower() not in {"", "null", "none", "~"}


def validate_config_contract_issues(config: dict[str, Any]) -> list[str]:
    """Return human-readable config drift issues for doctor (empty if OK)."""
    issues: list[str] = []
    if not isinstance(config, dict):
        return ["workspace config root must be a mapping"]

    for key in config:
        if key == "path":
            issues.append(
                "unsupported config key 'path' (removed; artifacts always live under .onward/ at the workspace root)"
            )
        elif key not in CONFIG_TOP_LEVEL_KEYS:
            issues.append(f"unsupported config key {key!r}")

    for section, allowed in CONFIG_SECTION_KEYS.items():
        if section not in config:
            continue
        block = config[section]
        if block is None:
            issues.append(f"config.{section} must be a mapping (got null)")
            continue
        if not isinstance(block, dict):
            issues.append(f"config.{section} must be a mapping")
            continue
        for k in block:
            path = f"{section}.{k}"
            if section == "work" and k in _REMOVED_WORK_KEYS:
                issues.append(
                    f"unsupported config key {path!r} (removed; execution git worktrees are not configurable)"
                )
            elif k not in allowed:
                issues.append(f"unsupported config key {path!r}")

    ralph = config.get("ralph")
    if isinstance(ralph, dict) and "args" in ralph and not isinstance(ralph.get("args"), list):
        issues.append("config.ralph.args must be a list")

    hooks = config.get("hooks")
    if isinstance(hooks, dict):
        for hk in ("pre_task_shell", "post_task_shell"):
            if hk in hooks and not isinstance(hooks.get(hk), list):
                issues.append(f"config.hooks.{hk} must be a list")

    sync = config.get("sync")
    if isinstance(sync, dict):
        mode = clean_string(sync.get("mode", "local")).lower() or "local"
        if mode == "local" and _repo_value_set(sync.get("repo")):
            issues.append(
                'sync.mode is "local" but sync.repo is set (repo is ignored until sync.mode is "repo")'
            )
        if mode == "branch" and _repo_value_set(sync.get("repo")):
            issues.append(
                'sync.mode is "branch" but sync.repo is set (repo is ignored in branch mode)'
            )

    return issues


def load_workspace_config(root: Path) -> dict[str, Any]:
    config_path = root / ".onward.config.yaml"
    if not config_path.exists():
        return {}
    parsed = parse_simple_yaml(config_path.read_text(encoding="utf-8"))
    if isinstance(parsed, dict):
        return parsed
    return {}


def is_ralph_enabled(config: dict[str, Any]) -> bool:
    """When false, task work, plan review, and markdown hooks must not invoke the executor."""
    ralph = config.get("ralph", {})
    if not isinstance(ralph, dict):
        return True
    if "enabled" not in ralph:
        return True
    return normalize_bool(ralph.get("enabled"))


def work_sequential_by_default(config: dict[str, Any]) -> bool:
    """When false, `onward work CHUNK` runs at most one ready task per invocation."""
    work = config.get("work", {})
    if not isinstance(work, dict):
        return True
    if "sequential_by_default" not in work:
        return True
    return normalize_bool(work.get("sequential_by_default"))


def model_setting(config: dict[str, Any], key: str, fallback: str) -> str:
    models = config.get("models", {})
    if isinstance(models, dict):
        value = str(models.get(key, "")).strip()
        if value:
            return value
    return fallback


def resolve_model_alias(model: str) -> str:
    normalized = model.strip().lower().replace("_", "-")
    if normalized.endswith("-latest"):
        family = normalized[: -len("-latest")]
        if family in MODEL_FAMILIES:
            return MODEL_FAMILIES[family]
    if normalized in MODEL_FAMILIES:
        return MODEL_FAMILIES[normalized]
    return model.strip()


def load_artifact_template(root: Path, artifact_type: str) -> str:
    return (root / f".onward/templates/{artifact_type}.md").read_text(encoding="utf-8")


def _load_prompt(root: Path, prompt_name: str) -> str:
    return (root / f".onward/prompts/{prompt_name}").read_text(encoding="utf-8")
