from __future__ import annotations

from pathlib import Path
from typing import Any

from onward.util import _clean_string, _parse_simple_yaml

MODEL_FAMILIES: dict[str, str] = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4",
    "codex": "codex-5-3",
    "gpt5": "gpt-5",
}


def _load_config(root: Path) -> dict[str, Any]:
    config_path = root / ".onward.config.yaml"
    if not config_path.exists():
        return {}
    parsed = _parse_simple_yaml(config_path.read_text(encoding="utf-8"))
    if isinstance(parsed, dict):
        return parsed
    return {}


def _config_model(config: dict[str, Any], key: str, fallback: str) -> str:
    models = config.get("models", {})
    if isinstance(models, dict):
        value = str(models.get(key, "")).strip()
        if value:
            return value
    return fallback


def _model_alias(model: str) -> str:
    normalized = model.strip().lower().replace("_", "-")
    if normalized.endswith("-latest"):
        family = normalized[: -len("-latest")]
        if family in MODEL_FAMILIES:
            return MODEL_FAMILIES[family]
    if normalized in MODEL_FAMILIES:
        return MODEL_FAMILIES[normalized]
    return model.strip()


def _load_template(root: Path, artifact_type: str) -> str:
    return (root / f".onward/templates/{artifact_type}.md").read_text(encoding="utf-8")


def _load_prompt(root: Path, prompt_name: str) -> str:
    return (root / f".onward/prompts/{prompt_name}").read_text(encoding="utf-8")
