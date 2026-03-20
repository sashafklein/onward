from __future__ import annotations

from dataclasses import dataclass
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
# ``ralph`` is accepted for backward compatibility; prefer ``executor``.
CONFIG_TOP_LEVEL_KEYS = frozenset({"version", "sync", "executor", "ralph", "models", "review", "work", "hooks"})

_EXECUTOR_SECTION_KEYS = frozenset({"command", "args", "enabled"})

CONFIG_SECTION_KEYS: dict[str, frozenset[str]] = {
    "sync": frozenset({"mode", "branch", "repo", "worktree_path"}),
    "executor": _EXECUTOR_SECTION_KEYS,
    "ralph": _EXECUTOR_SECTION_KEYS,
    "models": frozenset({"default", "task_default", "split_default", "review_default"}),
    "review": frozenset({"double_review", "reviewers"}),
    "work": frozenset({"sequential_by_default", "require_success_ack"}),
    "hooks": frozenset({
        "pre_task_shell",
        "post_task_shell",
        "pre_task_markdown",
        "post_task_markdown",
        "post_chunk_markdown",
    }),
}

_REMOVED_WORK_KEYS = frozenset({"create_worktree", "worktree_root", "base_branch"})


def _migrate_ralph_to_executor(config: dict[str, Any]) -> dict[str, Any]:
    """If only legacy ``ralph`` is set, copy it to ``executor`` (mutates ``config``)."""
    if "ralph" in config and "executor" not in config:
        config["executor"] = config["ralph"]
    return config


def config_raw_deprecation_warnings(raw_config: dict[str, Any]) -> list[str]:
    """Warnings for ``onward doctor`` when legacy top-level ``ralph`` appears on disk."""
    if not isinstance(raw_config, dict):
        return []
    has_ralph = "ralph" in raw_config
    has_executor = "executor" in raw_config
    if has_ralph and not has_executor:
        return ["config key 'ralph' is deprecated; rename to 'executor'"]
    if has_ralph and has_executor:
        return ["config key 'ralph' is deprecated and ignored; use 'executor' only"]
    return []


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

    review = config.get("review")
    if isinstance(review, dict):
        revw = review.get("reviewers")
        if revw is not None and not isinstance(revw, list):
            issues.append("config.review.reviewers must be a list when set")

    for section_name in ("executor", "ralph"):
        block = config.get(section_name)
        if isinstance(block, dict) and "args" in block and not isinstance(block.get("args"), list):
            issues.append(f"config.{section_name}.args must be a list")

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
        return _migrate_ralph_to_executor(parsed)
    return {}


def is_executor_enabled(config: dict[str, Any]) -> bool:
    """When false, task work, plan review, and markdown hooks must not invoke the executor."""
    block = config.get("executor", {})
    if not isinstance(block, dict):
        return True
    if "enabled" not in block:
        return True
    return normalize_bool(block.get("enabled"))


def work_sequential_by_default(config: dict[str, Any]) -> bool:
    """When false, `onward work CHUNK` runs at most one ready task per invocation."""
    work = config.get("work", {})
    if not isinstance(work, dict):
        return True
    if "sequential_by_default" not in work:
        return True
    return normalize_bool(work.get("sequential_by_default"))


def work_require_success_ack(config: dict[str, Any]) -> bool:
    """When true, a successful task run requires a machine-readable acknowledgment on executor output."""
    work = config.get("work", {})
    if not isinstance(work, dict):
        return False
    if "require_success_ack" not in work:
        return False
    return normalize_bool(work.get("require_success_ack"))


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


@dataclass(frozen=True)
class PlanReviewTry:
    """One executor attempt for a plan review slot (model + argv)."""

    model_resolved: str
    executor: str
    executor_args: tuple[str, ...]


@dataclass(frozen=True)
class PlanReviewSlot:
    """Ordered tries for a single reviewer label (primary then fallbacks)."""

    label: str
    tries: tuple[PlanReviewTry, ...]


def _workspace_executor_argv(config: dict[str, Any]) -> tuple[str, list[str]]:
    block = config.get("executor", {})
    if not isinstance(block, dict):
        block = {}
    command = clean_string(block.get("command")) or "onward-exec"
    args = block.get("args", [])
    if not isinstance(args, list):
        args = []
    return command, [str(x) for x in args]


def _review_executor_from_entry(entry: dict[str, Any], config: dict[str, Any]) -> tuple[str, list[str]]:
    cmd = clean_string(str(entry.get("command", "")))
    if cmd:
        args = entry.get("args")
        if isinstance(args, list):
            return cmd, [str(x) for x in args]
        return cmd, []
    return _workspace_executor_argv(config)


def _parse_review_fallback_try(
    fb: Any,
    inherited: tuple[str, list[str]],
    config: dict[str, Any],
) -> tuple[PlanReviewTry | None, str | None]:
    inh_exe, inh_args = inherited
    if isinstance(fb, str):
        m = fb.strip()
        if not m:
            return None, "empty fallback model"
        return PlanReviewTry(resolve_model_alias(m), inh_exe, tuple(inh_args)), None
    if isinstance(fb, dict):
        raw = str(fb.get("model", "")).strip()
        if not raw:
            return None, "fallback entry missing model"
        m = resolve_model_alias(raw)
        if clean_string(str(fb.get("command", ""))):
            exe, args = _review_executor_from_entry(fb, config)
        else:
            exe, args = inh_exe, inh_args
        return PlanReviewTry(m, exe, tuple(args)), None
    return None, "fallback must be a string (model) or mapping"


def _legacy_plan_review_slots(config: dict[str, Any]) -> list[PlanReviewSlot]:
    review_cfg = config.get("review", {})
    if not isinstance(review_cfg, dict):
        review_cfg = {}
    double = review_cfg.get("double_review", True)
    if isinstance(double, str):
        double = double.strip().lower() in {"1", "true", "yes", "y"}

    default_model = model_setting(config, "default", "opus-latest")
    review_model = model_setting(config, "review_default", default_model)
    exe, args = _workspace_executor_argv(config)
    base_try = PlanReviewTry(resolve_model_alias(review_model), exe, tuple(args))
    slots = [PlanReviewSlot(label="reviewer-1", tries=(base_try,))]
    if double:
        second = PlanReviewTry(resolve_model_alias(default_model), exe, tuple(args))
        slots.append(PlanReviewSlot(label="reviewer-2", tries=(second,)))
    return slots


def build_plan_review_slots(config: dict[str, Any]) -> tuple[list[PlanReviewSlot], str | None]:
    """Resolve review-plan slots from config.

    When ``review.reviewers`` is absent, empty, or null, uses ``double_review`` and
    ``models.review_default`` / ``models.default`` (legacy behavior).

    Returns ``([], err)`` on invalid ``reviewers`` shape.
    """
    review_cfg = config.get("review", {})
    if not isinstance(review_cfg, dict):
        review_cfg = {}
    reviewers = review_cfg.get("reviewers")
    if reviewers is None:
        return _legacy_plan_review_slots(config), None
    if not isinstance(reviewers, list):
        return [], "review.reviewers must be a list when set"
    if len(reviewers) == 0:
        return _legacy_plan_review_slots(config), None

    slots: list[PlanReviewSlot] = []
    for i, raw in enumerate(reviewers):
        if not isinstance(raw, dict):
            return [], f"review.reviewers[{i}] must be a mapping"
        entry = raw
        label = clean_string(str(entry.get("label", "")))
        if not label:
            label = f"reviewer-{i + 1}"
        raw_model = str(entry.get("model", "")).strip()
        if not raw_model:
            return [], f"review.reviewers[{i}] ({label!r}) missing model"
        exe, args = _review_executor_from_entry(entry, config)
        inherited: tuple[str, list[str]] = (exe, list(args))
        tries_list: list[PlanReviewTry] = [
            PlanReviewTry(resolve_model_alias(raw_model), exe, tuple(args)),
        ]
        fallback = entry.get("fallback")
        if fallback is not None:
            if not isinstance(fallback, list):
                return [], f"review.reviewers[{i}] ({label!r}) fallback must be a list"
            for j, fb in enumerate(fallback):
                tr, err = _parse_review_fallback_try(fb, inherited, config)
                if err:
                    return [], f"review.reviewers[{i}] ({label!r}) fallback[{j}]: {err}"
                assert tr is not None
                tries_list.append(tr)
        slots.append(PlanReviewSlot(label=label, tries=tuple(tries_list)))
    return slots, None


def load_artifact_template(root: Path, artifact_type: str) -> str:
    return (root / f".onward/templates/{artifact_type}.md").read_text(encoding="utf-8")


def _load_prompt(root: Path, prompt_name: str) -> str:
    return (root / f".onward/prompts/{prompt_name}").read_text(encoding="utf-8")
