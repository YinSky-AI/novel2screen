from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FidelityReport:
    passed: bool
    fabricated_characters: list[str] = field(default_factory=list)
    fabricated_locations: list[str] = field(default_factory=list)
    missing_elements: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class FidelityChecker:
    def __init__(self, character_names: set[str], location_names: set[str]) -> None:
        self.character_names = character_names
        self.location_names = location_names

    def check(self, screenplay_data: dict[str, Any]) -> FidelityReport:
        fabricated_chars = detect_fabricated_characters(
            screenplay_data.get("characters", []), self.character_names
        )
        fabricated_locs = detect_fabricated_locations(
            screenplay_data, self.location_names
        )
        warnings: list[str] = []

        passed = not fabricated_chars and not fabricated_locs
        if fabricated_chars:
            warnings.append(f"Fabricated characters: {fabricated_chars}")
        if fabricated_locs:
            warnings.append(f"Fabricated locations: {fabricated_locs}")

        return FidelityReport(
            passed=passed,
            fabricated_characters=fabricated_chars,
            fabricated_locations=fabricated_locs,
            warnings=warnings,
        )


def detect_fabricated_characters(
    screenplay_characters: list[dict[str, Any]],
    source_characters: set[str],
) -> list[str]:
    if not source_characters:
        return []
    fabricated: list[str] = []
    for c in screenplay_characters:
        name = c.get("name", "")
        if name and name not in source_characters:
            fabricated.append(name)
    return fabricated


def detect_fabricated_locations(
    screenplay_data: dict[str, Any],
    source_locations: set[str],
) -> list[str]:
    if not source_locations:
        return []
    locations_found: set[str] = set()
    episodes = screenplay_data.get("episodes", [])
    for ep in episodes:
        for sc in ep.get("scenes", []):
            loc = sc.get("location", "")
            if loc:
                locations_found.add(loc)
    return sorted(loc for loc in locations_found if loc not in source_locations)


def validate_character_ids_in_episodes(
    episodes: list[dict[str, Any]],
    valid_character_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    for ep in episodes:
        for sc in ep.get("scenes", []):
            for beat in sc.get("beats", []):
                char_id = beat.get("character_id")
                if char_id and char_id not in valid_character_ids:
                    errors.append(f"Unknown character '{char_id}' in scene {sc.get('scene_id', '?')}")
    return errors


def run_fidelity_check(
    screenplay: dict[str, Any],
    original_text: str,
) -> FidelityReport:
    return FidelityChecker(
        character_names=set(),
        location_names=set(),
    ).check(screenplay)
