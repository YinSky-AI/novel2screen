from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from backend.config import settings

logger = logging.getLogger(__name__)

_BUILTIN_CATEGORIES: dict[str, dict[str, Any]] = {}

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PromptLoader:
    def __init__(self, prompts_dir: str | None = None) -> None:
        self._prompts_dir: Path = Path(prompts_dir) if prompts_dir else _PROMPTS_DIR
        self._cache: dict[str, dict[str, Any]] = {}

    def load_category(self, category: str) -> dict[str, Any]:
        if category in self._cache:
            return self._cache[category]

        yaml_path = self._prompts_dir / f"{category}.yaml"
        yml_path = self._prompts_dir / f"{category}.yml"

        for path in (yaml_path, yml_path):
            if path.exists():
                try:
                    with open(path, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        self._cache[category] = data
                        logger.debug("Loaded prompts from %s", path)
                        return data
                except Exception as e:
                    logger.warning("Failed to load %s: %s", path, e)

        fallback = self._get_fallback(category)
        self._cache[category] = fallback
        return fallback

    def get_prompt(self, category: str, key: str, default: str = "") -> str:
        cat = self.load_category(category)
        return cat.get(key, default)

    def get_system_prompt(self, category: str, version: str = "v1") -> str:
        if version == "v1":
            return self.get_prompt(category, "system", "")
        key = f"system_{version}"
        return self.get_prompt(category, key, self.get_prompt(category, "system", ""))

    def get_user_template(self, category: str, version: str = "v1") -> str:
        if version == "v1":
            return self.get_prompt(category, "user", "")
        key = f"user_{version}"
        return self.get_prompt(category, key, self.get_prompt(category, "user", ""))

    def available_categories(self) -> list[str]:
        cats: set[str] = set(_BUILTIN_CATEGORIES.keys())
        if self._prompts_dir.exists():
            for f in self._prompts_dir.iterdir():
                if f.suffix in (".yaml", ".yml"):
                    cats.add(f.stem)
        return sorted(cats)

    def clear_cache(self) -> None:
        self._cache.clear()

    @staticmethod
    def _get_fallback(category: str) -> dict[str, Any]:
        from backend.core import prompts as _p

        mapping: dict[str, dict[str, Any]] = {
            "narrative": {"system": _p.NARRATIVE_SYSTEM, "user": _p.NARRATIVE_USER},
            "character": {"system": _p.CHARACTER_SYSTEM, "user": _p.CHARACTER_USER},
            "world": {"system": _p.WORLD_SYSTEM, "user": _p.WORLD_USER},
            "timeline": {"system": _p.TIMELINE_SYSTEM, "user": _p.TIMELINE_USER},
            "episode_planner": {"system": _p.EPISODE_PLANNER_SYSTEM, "user": _p.EPISODE_PLANNER_USER},
            "scene_planner": {"system": _p.SCENE_PLANNER_SYSTEM, "user": _p.SCENE_PLANNER_USER},
            "dialogue": {"system": _p.DIALOGUE_SYSTEM, "user": _p.DIALOGUE_USER},
            "critic": {"system": _p.CRITIC_SYSTEM, "user": _p.CRITIC_USER},
            "repair": {"system": _p.REPAIR_SYSTEM, "user": _p.REPAIR_USER},
            "consistency": {"system": _p.CONSISTENCY_SYSTEM, "user": _p.CONSISTENCY_USER},
            "preprocess": {"system": _p.PREPROCESS_SYSTEM, "user": _p.PREPROCESS_USER},
            "batch_plan": {"system": _p.BATCH_PLAN_SYSTEM, "user": _p.BATCH_PLAN_USER},
            "fast_critic": {"system": _p.FAST_CRITIC, "user": "{scene_content}"},
        }
        return mapping.get(category, {"system": "", "user": ""})
