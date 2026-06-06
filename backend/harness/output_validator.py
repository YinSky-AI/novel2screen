from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationReport:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class OutputValidator:
    @staticmethod
    def validate_emotion_labels(emotions: list[str]) -> ValidationReport:
        valid_emotions = {
            "anger", "fear", "joy", "sadness", "surprise", "disgust", "trust",
            "anticipation", "neutral", "love", "hate", "hope", "despair",
            "紧张", "恐惧", "喜悦", "悲伤", "惊讶", "愤怒", "平静",
            "震惊", "绝望", "决心", "犹豫", "神秘", "震撼", "警觉",
            "困惑", "希望", "冷静", "感动", "兴奋", "失望", "疲惫",
        }
        invalid = [e for e in emotions if e and e not in valid_emotions]
        if invalid:
            return ValidationReport(
                valid=False,
                warnings=[f"Unrecognized emotion labels: {invalid}"],
            )
        return ValidationReport(valid=True)

    @staticmethod
    def validate_character_ids_in_episodes(
        episode_data: list[dict[str, Any]],
        character_ids: set[str],
    ) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        for ep in episode_data:
            for sc in ep.get("scenes", []):
                for beat in sc.get("beats", []):
                    char_id = beat.get("character_id")
                    if char_id and char_id not in character_ids:
                        errors.append(
                            f"Unknown character {char_id} in scene {sc.get('scene_id', '?')}"
                        )
        return ValidationReport(valid=len(errors) == 0, errors=errors, warnings=warnings)

    @staticmethod
    def validate_scene_ids(scenes: list[dict[str, Any]]) -> ValidationReport:
        scene_ids = [s.get("scene_id") for s in scenes if s.get("scene_id")]
        duplicates = {sid for sid in scene_ids if scene_ids.count(sid) > 1}
        if duplicates:
            return ValidationReport(
                valid=False,
                errors=[f"Duplicate scene IDs: {duplicates}"],
            )
        return ValidationReport(valid=True)

    @staticmethod
    def validate_transitions(scenes: list[dict[str, Any]]) -> ValidationReport:
        valid_transitions = {"cut", "fade", "dissolve", "wipe"}
        errors: list[str] = []
        for sc in scenes:
            transition = sc.get("transition", "cut")
            if transition not in valid_transitions:
                errors.append(f"Invalid transition '{transition}' in scene {sc.get('scene_id', '?')}")
        return ValidationReport(valid=len(errors) == 0, errors=errors)

    @staticmethod
    def validate_beat_types(beats: list[dict[str, Any]]) -> ValidationReport:
        valid_types = {"dialogue", "action", "silence", "reaction"}
        errors: list[str] = []
        for i, beat in enumerate(beats):
            if beat.get("type") not in valid_types:
                errors.append(f"Beat {i}: invalid type '{beat.get('type')}'")
        return ValidationReport(valid=len(errors) == 0, errors=errors)


__all__ = ["OutputValidator", "ValidationReport"]
