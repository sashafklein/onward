from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from onward.executor import Executor

from onward.util import clean_string, normalize_bool, parse_simple_yaml


@dataclass(frozen=True)
class WorkspaceLayout:
    """Encapsulates artifact directory path resolution for single-root and multi-root workspaces.

    The `roots` dict maps project keys to their artifact root paths:
    - Single-root mode (default or `root: nb`): `{None: Path(".onward")}` or `{None: Path("nb")}`
    - Multi-root mode (`roots: {a: .a, b: .b}`): `{"a": Path(".a"), "b": Path(".b")}`

    All path resolution methods accept an optional `project` parameter. In single-root mode,
    `project` is ignored (always resolves to the single root). In multi-root mode without a
    `default_project`, `project` must be provided or a ValueError is raised.
    """

    workspace_root: Path
    roots: dict[str | None, Path]  # project key -> absolute artifact root
    default_project: str | None

    @classmethod
    def from_config(cls, root: Path, config: dict[str, Any]) -> "WorkspaceLayout":
        """Create a WorkspaceLayout from workspace root and parsed config.

        Args:
            root: Absolute path to the workspace root (where .onward.config.yaml lives)
            config: Parsed config dict (may be empty)

        Returns:
            WorkspaceLayout instance with resolved artifact root paths

        Config keys processed:
            - `root` (str): Single custom artifact root (mutually exclusive with `roots`)
            - `roots` (dict): Multi-project artifact roots `{project_key: path, ...}`
            - `default_project` (str): Default project key when `roots` is set

        When neither `root` nor `roots` is set, defaults to `.onward/` (backward compatible).
        """
        if not isinstance(config, dict):
            config = {}

        config_root = config.get("root")
        config_roots = config.get("roots")
        default_project = config.get("default_project")

        # Normalize default_project
        if default_project is not None:
            default_project = str(default_project).strip() or None

        # Case 1: Multi-root mode (roots dict provided)
        if config_roots is not None:
            if not isinstance(config_roots, dict):
                # Invalid, but we'll just fall back to default
                roots_map = {None: root / ".onward"}
                default_project = None
            else:
                roots_map = {}
                for key, path_str in config_roots.items():
                    key_str = str(key).strip()
                    if not key_str or not path_str:
                        continue
                    path = Path(path_str)
                    if not path.is_absolute():
                        path = root / path
                    roots_map[key_str] = path.resolve()

                # If roots is empty after parsing, fall back to default
                if not roots_map:
                    roots_map = {None: root / ".onward"}
                    default_project = None

            return cls(
                workspace_root=root,
                roots=roots_map,
                default_project=default_project,
            )

        # Case 2: Single custom root (root key provided)
        if config_root is not None:
            root_str = str(config_root).strip()
            if root_str:
                custom_path = Path(root_str)
                if not custom_path.is_absolute():
                    custom_path = root / custom_path
                return cls(
                    workspace_root=root,
                    roots={None: custom_path.resolve()},
                    default_project=None,
                )

        # Case 3: Default (no root or roots configured)
        return cls(
            workspace_root=root,
            roots={None: root / ".onward"},
            default_project=None,
        )

    @property
    def is_multi_root(self) -> bool:
        """True if multiple project roots are configured (len(roots) > 1)."""
        # If we have any non-None key, we're in multi-root mode
        return any(k is not None for k in self.roots.keys())

    def all_project_keys(self) -> list[str | None]:
        """Return all configured project keys (or [None] in single-root mode)."""
        return list(self.roots.keys())

    def artifact_root(self, project: str | None = None) -> Path:
        """Resolve the artifact root directory for a project.

        Args:
            project: Project key (required in multi-root mode without default_project)

        Returns:
            Absolute path to the artifact root directory

        Raises:
            ValueError: If project is required but not provided
        """
        # Single-root mode: always use the single root
        if not self.is_multi_root:
            return self.roots[None]

        # Multi-root mode: resolve project
        if project is None:
            if self.default_project is not None:
                project = self.default_project
            else:
                available = [k for k in self.roots.keys() if k is not None]
                raise ValueError(
                    f"Multiple projects configured. Use --project <name> (available: {', '.join(available)})"
                )

        if project not in self.roots:
            available = [k for k in self.roots.keys() if k is not None]
            raise ValueError(
                f"Unknown project {project!r}. Available projects: {', '.join(available)}"
            )

        return self.roots[project]

    def plans_dir(self, project: str | None = None) -> Path:
        """Resolve the plans directory for a project."""
        return self.artifact_root(project) / "plans"

    def runs_dir(self, project: str | None = None) -> Path:
        """Resolve the runs directory for a project."""
        return self.artifact_root(project) / "runs"

    def reviews_dir(self, project: str | None = None) -> Path:
        """Resolve the reviews directory for a project."""
        return self.artifact_root(project) / "reviews"

    def templates_dir(self, project: str | None = None) -> Path:
        """Resolve the templates directory for a project."""
        return self.artifact_root(project) / "templates"

    def prompts_dir(self, project: str | None = None) -> Path:
        """Resolve the prompts directory for a project."""
        return self.artifact_root(project) / "prompts"

    def hooks_dir(self, project: str | None = None) -> Path:
        """Resolve the hooks directory for a project."""
        return self.artifact_root(project) / "hooks"

    def notes_dir(self, project: str | None = None) -> Path:
        """Resolve the notes directory for a project."""
        return self.artifact_root(project) / "notes"

    def one_offs_dir(self, project: str | None = None) -> Path:
        """Resolve the one-offs directory for a project."""
        return self.artifact_root(project) / "one-offs"

    def sync_dir(self, project: str | None = None) -> Path:
        """Resolve the sync directory for a project."""
        return self.artifact_root(project) / "sync"

    def ongoing_path(self, project: str | None = None) -> Path:
        """Resolve the ongoing.json path for a project."""
        return self.artifact_root(project) / "ongoing.json"

    def index_path(self, project: str | None = None) -> Path:
        """Resolve the index.yaml path for a project."""
        return self.artifact_root(project) / "plans" / "index.yaml"

    def recent_path(self, project: str | None = None) -> Path:
        """Resolve the recent.yaml path for a project."""
        return self.artifact_root(project) / "plans" / "recent.yaml"

    def archive_dir(self, project: str | None = None) -> Path:
        """Resolve the archive directory for a project."""
        return self.artifact_root(project) / "plans" / ".archive"


# Declared keys for `.onward.config.yaml` (unknown keys fail `onward doctor`).
# ``ralph`` is accepted for backward compatibility; prefer ``executor``.
CONFIG_TOP_LEVEL_KEYS = frozenset({
    "version", "sync", "executor", "ralph", "models", "review", "work", "hooks",
    "root", "roots", "default_project", "linear"
})

_EXECUTOR_SECTION_KEYS = frozenset({"command", "args", "enabled"})

CONFIG_SECTION_KEYS: dict[str, frozenset[str]] = {
    "sync": frozenset({"mode", "branch", "repo", "worktree_path"}),
    "executor": _EXECUTOR_SECTION_KEYS,
    "ralph": _EXECUTOR_SECTION_KEYS,
    "models": frozenset({
        "default",
        "high",
        "medium",
        "low",
        "split",
        "review_1",
        "review_2",
        # Legacy flat keys (read as aliases; doctor warns — migrate to tier keys).
        "task_default",
        "split_default",
        "review_default",
    }),
    "review": frozenset({"double_review", "reviewers"}),
    "work": frozenset({"sequential_by_default", "require_success_ack", "max_retries", "claim_timeout_minutes", "max_parallel_tasks"}),
    "hooks": frozenset({
        "pre_task_shell",
        "post_task_shell",
        "pre_chunk_shell",
        "post_task_markdown",
        "post_chunk_markdown",
    }),
    "linear": frozenset({"team_id"}),
}

_REMOVED_WORK_KEYS = frozenset({"create_worktree", "worktree_root", "base_branch"})

# Tier fallbacks after the tier's own value (see PLAN-012 tiered models).
_MODEL_TIER_FALLBACKS: dict[str, tuple[str, ...]] = {
    "high": ("default",),
    "medium": ("high", "default"),
    "low": ("medium", "high", "default"),
    "split": ("default",),
    "review_1": ("high", "default"),
    "review_2": ("high", "default"),
}

_MODEL_TIER_NAMES = frozenset(_MODEL_TIER_FALLBACKS.keys())

# Keys under ``models`` whose values are model id strings or YAML null (tier fallbacks).
_MODEL_SCALAR_KEYS = frozenset(
    {
        "default",
        "high",
        "medium",
        "low",
        "split",
        "review_1",
        "review_2",
        "task_default",
        "split_default",
        "review_default",
    },
)

# Effort frontmatter values that map to tier names (unknown values use the default tier).
_EFFORT_TIER_VALUES = frozenset({"high", "medium", "low"})

# Legacy flat keys still read by `model_setting()` when present; map to tiers when absent.
_LEGACY_MODEL_KEY_TO_TIER = {
    "task_default": "medium",
    "split_default": "split",
    "review_default": "review_1",
}

# When resolving tier ``split`` / ``review_1``, fall back to these legacy keys if the tier key is empty.
_TIER_LEGACY_MODEL_KEY: dict[str, str] = {
    "split": "split_default",
    "review_1": "review_default",
}


MODEL_ALIASES: dict[str, str] = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4",
    "codex": "codex-5-3",
}


def resolve_model_alias(model: str) -> str:
    """Resolve a short alias to a canonical model identifier.

    Lookup is case-insensitive.  Unknown strings are returned unchanged.
    """
    if not model:
        return model
    return MODEL_ALIASES.get(model.strip().lower(), model)


def _nonempty_model_string(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    return s


def _tier_effective_model_string(models: dict[str, Any], tier_key: str) -> str:
    """Value for a tier key, including legacy ``split_default`` / ``review_default`` aliases."""
    v = _nonempty_model_string(models.get(tier_key))
    if v:
        return v
    legacy = _TIER_LEGACY_MODEL_KEY.get(tier_key)
    if legacy:
        return _nonempty_model_string(models.get(legacy))
    return ""


def effective_default_model(config: dict[str, Any]) -> str:
    """Resolved ``models.default``, or ``opus`` when unset or empty."""
    models = config.get("models", {})
    if not isinstance(models, dict):
        return "opus"
    s = _nonempty_model_string(models.get("default"))
    return s if s else "opus"


def resolve_model_for_tier(config: dict[str, Any], tier_name: str) -> str:
    """Resolve a model for a tier, walking automatic fallback keys until non-empty.

    Legacy ``models.split_default`` / ``models.review_default`` are used when ``split`` /
    ``review_1`` are empty (non-empty tier keys win). ``task_default`` is not a tier alias here.

    ``models.default`` is required logically; when missing or empty, ``opus`` is used
    as the ultimate default (same as historical ``model_setting(..., "default", "opus")``).
    """
    models = config.get("models", {})
    if not isinstance(models, dict):
        models = {}

    default_eff = effective_default_model(config)
    if tier_name == "default":
        return default_eff

    chain = _MODEL_TIER_FALLBACKS.get(tier_name)
    if chain is None:
        return default_eff

    for k in (tier_name,) + chain:
        if k == "default":
            val = default_eff
        else:
            val = _tier_effective_model_string(models, k)
        if val:
            return val
    return default_eff


def resolve_model_for_task(config: dict[str, Any], task_metadata: Mapping[str, Any]) -> str:
    """Pick the executor model for a task from config and artifact metadata.

    Resolution order:

    1. Non-empty ``task_metadata["model"]`` — returned as-is.
    2. ``task_metadata["complexity"]`` of ``high`` / ``medium`` / ``low`` (case-insensitive) —
       :func:`resolve_model_for_tier` for that tier. Falls back to legacy ``effort`` key
       for backward compatibility with tasks still using the old name.
    3. Otherwise — :func:`resolve_model_for_tier` for ``"default"``.

    Other complexity strings (e.g. ``xl``) are ignored for tier mapping and behave like step 3.
    """
    explicit = _nonempty_model_string(task_metadata.get("model"))
    if explicit:
        return explicit

    raw_complexity = task_metadata.get("complexity")
    if raw_complexity is None:  # compat: fall back to legacy 'effort' key
        raw_complexity = task_metadata.get("effort")
    if raw_complexity is not None:
        e = str(raw_complexity).strip().lower()
        if e in _EFFORT_TIER_VALUES:
            return resolve_model_for_tier(config, e)

    return resolve_model_for_tier(config, "default")


def _migrate_ralph_to_executor(config: dict[str, Any]) -> dict[str, Any]:
    """If only legacy ``ralph`` is set, copy it to ``executor`` (mutates ``config``)."""
    if "ralph" in config and "executor" not in config:
        config["executor"] = config["ralph"]
    return config


def config_raw_deprecation_warnings(raw_config: dict[str, Any]) -> list[str]:
    """Warnings for ``onward doctor`` when legacy config appears on disk."""
    if not isinstance(raw_config, dict):
        return []
    out: list[str] = []
    has_ralph = "ralph" in raw_config
    has_executor = "executor" in raw_config
    if has_ralph and not has_executor:
        out.append("config key 'ralph' is deprecated; rename to 'executor'")
    elif has_ralph and has_executor:
        out.append("config key 'ralph' is deprecated and ignored; use 'executor' only")

    models = raw_config.get("models")
    if isinstance(models, dict):
        if "task_default" in models:
            out.append(
                "config.models.task_default is deprecated; use models.medium (and task effort/model) "
                "for the default task tier"
            )
        if "split_default" in models:
            if _nonempty_model_string(models.get("split")) and _nonempty_model_string(models.get("split_default")):
                out.append(
                    "config.models.split_default is deprecated and ignored because models.split is set; "
                    "remove split_default"
                )
            else:
                out.append("config.models.split_default is deprecated; rename to models.split")
        if "review_default" in models:
            if _nonempty_model_string(models.get("review_1")) and _nonempty_model_string(
                models.get("review_default"),
            ):
                out.append(
                    "config.models.review_default is deprecated and ignored because models.review_1 is set; "
                    "remove review_default"
                )
            else:
                out.append("config.models.review_default is deprecated; rename to models.review_1")

    return out


def _repo_value_set(repo_val: Any) -> bool:
    if repo_val is None:
        return False
    return clean_string(str(repo_val)).lower() not in {"", "null", "none", "~"}


def validate_config_contract_issues(config: dict[str, Any]) -> list[str]:
    """Return human-readable config drift issues for doctor (empty if OK)."""
    issues: list[str] = []
    if not isinstance(config, dict):
        return ["workspace config root must be a mapping"]

    # Validate root/roots mutual exclusivity
    has_root = "root" in config and config.get("root") is not None
    has_roots = "roots" in config and config.get("roots") is not None
    if has_root and has_roots:
        issues.append("config keys 'root' and 'roots' are mutually exclusive (use one or the other)")

    # Validate root value
    if has_root:
        root_val = config.get("root")
        if not isinstance(root_val, str):
            issues.append("config.root must be a non-empty string")
        elif not str(root_val).strip():
            issues.append("config.root must be a non-empty string")

    # Validate roots value
    if has_roots:
        roots = config.get("roots")
        if not isinstance(roots, dict):
            issues.append("config.roots must be a non-empty mapping of project keys to paths")
        elif len(roots) == 0:
            issues.append("config.roots must be a non-empty mapping of project keys to paths")
        else:
            # Validate each key-value pair
            for key, value in roots.items():
                key_str = str(key).strip()
                if not key_str:
                    issues.append("config.roots keys must be non-empty strings")
                    break
                if not isinstance(value, str):
                    issues.append(f"config.roots[{key!r}] must be a non-empty string path")
                elif not str(value).strip():
                    issues.append(f"config.roots[{key!r}] must be a non-empty string path")

    # Validate default_project when roots is set
    if has_roots:
        roots = config.get("roots")
        if isinstance(roots, dict):
            default_proj = config.get("default_project")
            if default_proj is not None:
                default_proj_str = str(default_proj).strip()
                if default_proj_str and default_proj_str not in roots:
                    available = ", ".join(str(k) for k in roots.keys())
                    issues.append(
                        f"config.default_project {default_proj_str!r} does not match any key in roots "
                        f"(available: {available})"
                    )

    # Warn if default_project is set without roots
    if not has_roots and "default_project" in config and config.get("default_project") is not None:
        default_proj_str = str(config.get("default_project")).strip()
        if default_proj_str:
            issues.append(
                "config.default_project is set but config.roots is not configured "
                "(default_project is only used with multi-root workspaces)"
            )

    for key in config:
        if key == "path":
            issues.append(
                "unsupported config key 'path' (removed; use 'root' or 'roots' to configure artifact directories)"
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

    models = config.get("models")
    if isinstance(models, dict):
        for mk, mv in models.items():
            if mk not in _MODEL_SCALAR_KEYS:
                continue
            if mv is None:
                continue
            if not isinstance(mv, str):
                issues.append(f"config.models.{mk} must be a string or null when set")
            elif not str(mv).strip():
                issues.append(
                    f"config.models.{mk} must be a non-empty string when set (use null for tier fallback)",
                )

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
        for hk in ("pre_task_shell", "post_task_shell", "pre_chunk_shell"):
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


def config_validation_warnings(config: dict[str, Any]) -> list[str]:
    """Advisory messages for ``onward doctor`` (tiered models, built-in executor, routing hints)."""
    out: list[str] = []
    if not isinstance(config, dict):
        return out

    models = config.get("models")
    if not isinstance(models, dict):
        models = {}

    if not _nonempty_model_string(models.get("default")):
        out.append(
            "config.models.default is unset or empty; Onward falls back to opus. "
            "Set models.default explicitly.",
        )

    if is_executor_enabled(config):
        block = config.get("executor", {})
        if not isinstance(block, dict):
            block = {}
        cmd = clean_string(block.get("command"))
        uses_builtin = not cmd or cmd.lower() == "builtin"
        if uses_builtin and shutil.which("claude") is None and shutil.which("cursor") is None:
            out.append(
                "built-in executor is selected but neither 'claude' nor 'cursor' was found on PATH; "
                "install a CLI or set executor.command to an external executor",
            )

    from onward.executor_builtin import model_string_matches_cli_routing_hint

    for tier_k in sorted(_MODEL_SCALAR_KEYS):
        if tier_k not in models:
            continue
        raw = models.get(tier_k)
        if raw is None or not isinstance(raw, str):
            continue
        s = _nonempty_model_string(raw)
        if not s:
            continue
        if not model_string_matches_cli_routing_hint(s):
            out.append(
                f"config.models.{tier_k} model {s!r} does not match built-in CLI routing hints "
                f"(claude/codex/opus/sonnet/haiku vs cursor/gemini); it will use the Claude CLI backend",
            )

    return out


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


def work_max_retries(config: dict[str, Any]) -> int:
    """Max failed runs before ``onward work`` refuses (``run_count`` threshold). 0 = unlimited."""
    work = config.get("work", {})
    if not isinstance(work, dict) or "max_retries" not in work:
        return 3
    raw = work.get("max_retries")
    if raw is None or raw == "":
        return 3
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 3
    return max(0, n)


def work_claim_timeout_minutes(config: dict[str, Any]) -> int:
    """Minutes before a claim expires regardless of PID liveness.

    Default is 120 minutes. Setting to 0 disables claiming entirely
    (``claimed_task_ids`` returns an empty set).
    """
    work = config.get("work", {})
    if not isinstance(work, dict) or "claim_timeout_minutes" not in work:
        return 120
    raw = work.get("claim_timeout_minutes")
    if raw is None or raw == "":
        return 120
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 120
    return max(0, n)


def work_max_parallel_tasks(config: dict[str, Any]) -> int:
    """Max tasks to dispatch concurrently within a chunk. Default 1 (serial). Minimum 1."""
    work = config.get("work", {})
    if not isinstance(work, dict) or "max_parallel_tasks" not in work:
        return 1
    raw = work.get("max_parallel_tasks")
    if raw is None or raw == "":
        return 1
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 1
    return max(1, n)


def model_setting(config: dict[str, Any], key: str, fallback: str) -> str:
    """Read a model string from ``config.models``.

    Supports legacy keys ``task_default`` / ``split_default`` / ``review_default``: when those
    keys are absent or empty, resolution uses the matching tier (medium / split / review_1).
    Tier names and ``default`` use :func:`resolve_model_for_tier`.
    """
    models = config.get("models", {})
    if not isinstance(models, dict):
        return fallback

    direct = _nonempty_model_string(models.get(key))
    if direct:
        return direct

    legacy_tier = _LEGACY_MODEL_KEY_TO_TIER.get(key)
    if legacy_tier is not None:
        return resolve_model_for_tier(config, legacy_tier)

    if key == "default" or key in _MODEL_TIER_NAMES:
        return resolve_model_for_tier(config, key)

    return fallback


@dataclass(frozen=True)
class PlanReviewTry:
    """One executor attempt for a plan review slot (model + argv)."""

    model: str
    executor: str
    executor_args: tuple[str, ...]


@dataclass(frozen=True)
class PlanReviewSlot:
    """Ordered tries for a single reviewer label (primary then fallbacks)."""

    label: str
    tries: tuple[PlanReviewTry, ...]


def resolve_executor(config: dict[str, Any]) -> Executor:
    """Pick :class:`~onward.executor.SubprocessExecutor` vs :class:`~onward.executor.BuiltinExecutor`.

    When ``executor.command`` is set to a non-empty string other than ``\"builtin\"`` (case-insensitive),
    the external stdin-JSON protocol is used. Otherwise :class:`~onward.executor.BuiltinExecutor` runs
    Claude/Cursor CLIs directly.

    ``require_success_ack`` applies to both built-in and subprocess executors via :func:`work_require_success_ack`.
    """
    from onward.executor import BuiltinExecutor, SubprocessExecutor

    block = config.get("executor", {})
    if not isinstance(block, dict):
        return BuiltinExecutor(config)

    cmd = clean_string(block.get("command"))
    if cmd and cmd.lower() != "builtin":
        args = block.get("args", [])
        if not isinstance(args, list):
            args = []
        return SubprocessExecutor(
            cmd,
            [str(x) for x in args],
            require_success_ack=work_require_success_ack(config),
        )
    return BuiltinExecutor(config)


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
        return PlanReviewTry(m, inh_exe, tuple(inh_args)), None
    if isinstance(fb, dict):
        raw = str(fb.get("model", "")).strip()
        if not raw:
            return None, "fallback entry missing model"
        m = raw.strip()
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

    review_model = resolve_model_for_tier(config, "review_1")
    second_model = resolve_model_for_tier(config, "review_2")
    exe, args = _workspace_executor_argv(config)
    base_try = PlanReviewTry(review_model.strip(), exe, tuple(args))
    slots = [PlanReviewSlot(label="reviewer-1", tries=(base_try,))]
    if double:
        second = PlanReviewTry(second_model.strip(), exe, tuple(args))
        slots.append(PlanReviewSlot(label="reviewer-2", tries=(second,)))
    return slots


def build_plan_review_slots(config: dict[str, Any]) -> tuple[list[PlanReviewSlot], str | None]:
    """Resolve review-plan slots from config.

    When ``review.reviewers`` is absent, empty, or null, uses ``double_review`` and
    ``models.review_1`` / ``models.review_2`` (with tier fallbacks; see ``resolve_model_for_tier``).

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
            PlanReviewTry(raw_model.strip(), exe, tuple(args)),
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


def _resolve_with_fallback(
    layout: WorkspaceLayout,
    project: str | None,
    subdir: str,
    filename: str,
) -> Path:
    """Resolve a file path with project-specific and shared fallback.

    Lookup order:
    1. Project-specific directory (e.g., `<project_root>/templates/task.md`)
    2. Shared fallback directory (`.onward/<subdir>/<filename>`)
    3. FileNotFoundError if not found in either location

    Args:
        layout: WorkspaceLayout to use for path resolution
        project: Project key for multi-root workspaces (optional)
        subdir: Subdirectory name (e.g., "templates", "prompts", "hooks")
        filename: Filename to look up

    Returns:
        Path to the file (may or may not exist; caller should check/read)

    Raises:
        FileNotFoundError: If file not found in project-specific or shared location
    """
    # Primary: project-specific location
    if subdir == "templates":
        primary = layout.templates_dir(project) / filename
    elif subdir == "prompts":
        primary = layout.prompts_dir(project) / filename
    elif subdir == "hooks":
        primary = layout.hooks_dir(project) / filename
    else:
        # Unknown subdir, just construct the path
        primary = layout.artifact_root(project) / subdir / filename

    if primary.exists():
        return primary

    # Fallback: shared .onward/ directory (only in multi-root mode)
    if layout.is_multi_root:
        fallback = layout.workspace_root / ".onward" / subdir / filename
        if fallback.exists():
            return fallback

    # If primary doesn't exist and we're in single-root mode, or fallback doesn't exist
    # in multi-root mode, return the primary path. The caller will get FileNotFoundError
    # when they try to read it, with the project-specific path in the error message.
    return primary


def load_artifact_template(
    root: Path,
    artifact_type: str,
    layout: WorkspaceLayout | None = None,
    project: str | None = None,
) -> str:
    """Load an artifact template (plan, chunk, task).

    Lookup order (multi-root mode):
    1. Project-specific: `<project_root>/templates/{artifact_type}.md`
    2. Shared fallback: `.onward/templates/{artifact_type}.md`
    3. FileNotFoundError if not found

    Args:
        root: Workspace root directory (where .onward.config.yaml lives)
        artifact_type: Template name (e.g., "plan", "chunk", "task")
        layout: WorkspaceLayout to use for path resolution (defaults to .onward/)
        project: Project key for multi-root workspaces (optional)

    Returns:
        Template content as a string
    """
    if layout is None:
        # Backward compatibility: construct default layout when not provided
        layout = WorkspaceLayout(
            workspace_root=root,
            roots={None: root / ".onward"},
            default_project=None,
        )
    template_path = _resolve_with_fallback(layout, project, "templates", f"{artifact_type}.md")
    return template_path.read_text(encoding="utf-8")


def _load_prompt(
    root: Path,
    prompt_name: str,
    layout: WorkspaceLayout | None = None,
    project: str | None = None,
) -> str:
    """Load a prompt file (split.md, review.md, etc.).

    Lookup order (multi-root mode):
    1. Project-specific: `<project_root>/prompts/{prompt_name}`
    2. Shared fallback: `.onward/prompts/{prompt_name}`
    3. FileNotFoundError if not found

    Args:
        root: Workspace root directory (where .onward.config.yaml lives)
        prompt_name: Prompt filename (e.g., "split.md", "review.md")
        layout: WorkspaceLayout to use for path resolution (defaults to .onward/)
        project: Project key for multi-root workspaces (optional)

    Returns:
        Prompt content as a string
    """
    if layout is None:
        # Backward compatibility: construct default layout when not provided
        layout = WorkspaceLayout(
            workspace_root=root,
            roots={None: root / ".onward"},
            default_project=None,
        )
    prompt_path = _resolve_with_fallback(layout, project, "prompts", prompt_name)
    return prompt_path.read_text(encoding="utf-8")
