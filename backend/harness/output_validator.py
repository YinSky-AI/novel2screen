"""Output validator for screenplay YAML.
Validates beyond Pydantic schema: emotion labels, ending match, character consistency, plot fidelity.
"""
import re


class ValidationReport:
    """Structured report of validation results."""

    def __init__(self, passed: bool = True):
        self.passed = passed
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.score: float = 1.0

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.passed = False
        self.score = max(0.0, self.score - 0.15)

    def add_warning(self, msg: str):
        self.warnings.append(msg)
        self.score = max(0.0, self.score - 0.05)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "score": round(self.score, 2),
        }


def parse_screenplay_yaml(yaml_str: str) -> dict | None:
    """Parse YAML string safely, returning None on failure."""
    try:
        import yaml
        data = yaml.safe_load(yaml_str)
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


def validate_emotion_labels(data: dict, allowed_emotions: set, report: ValidationReport):
    """Check all emotion values are in the allowed set."""
    for ep_idx, ep in enumerate(data.get("episodes", [])):
        for sc_idx, sc in enumerate(ep.get("scenes", [])):
            for b_idx, beat in enumerate(sc.get("beats", [])):
                emo = beat.get("emotion")
                if emo and emo.lower() not in {e.lower() for e in allowed_emotions}:
                    loc = f"ep{ep_idx+1}/sc{sc_idx+1}/beat{b_idx+1}"
                    report.add_error(
                        f"Invalid emotion '{emo}' at {loc}. "
                        f"Allowed: {', '.join(sorted(allowed_emotions))}",
                    )


def validate_character_ids(data: dict, report: ValidationReport):
    """Check all dialogue beats reference valid character IDs."""
    char_ids = {c["id"] for c in data.get("characters", []) if "id" in c}
    for ep_idx, ep in enumerate(data.get("episodes", [])):
        for sc_idx, sc in enumerate(ep.get("scenes", [])):
            for b_idx, beat in enumerate(sc.get("beats", [])):
                cid = beat.get("character_id")
                if beat.get("type") == "dialogue" and (not cid or cid not in char_ids):
                    loc = f"ep{ep_idx+1}/sc{sc_idx+1}/beat{b_idx+1}"
                    if not cid:
                        report.add_error(f"Dialogue beat at {loc} missing character_id")
                    else:
                        report.add_warning(f"character_id '{cid}' at {loc} not found in characters list")


def validate_characters_present(data: dict, report: ValidationReport):
    """Check characters_present in each scene."""
    char_ids = {c["id"] for c in data.get("characters", []) if "id" in c}
    for ep_idx, ep in enumerate(data.get("episodes", [])):
        for sc_idx, sc in enumerate(ep.get("scenes", [])):
            loc = f"ep{ep_idx+1}/sc{sc_idx+1}"
            present = sc.get("characters_present", [])
            if not present:
                report.add_warning(f"Scene at {loc} missing characters_present")
            for cid in present:
                if cid not in char_ids:
                    report.add_warning(f"characters_present '{cid}' at {loc} not in character list")


def validate_ending(data: dict, novel_ending: str, report: ValidationReport):
    """Compare novel ending to last scene of screenplay."""
    episodes = data.get("episodes", [])
    if not episodes:
        report.add_warning("No episodes to validate ending against")
        return

    last_ep = episodes[-1]
    scenes = last_ep.get("scenes", [])
    if not scenes:
        report.add_warning("Last episode has no scenes")
        return

    last_scene = scenes[-1]
    beats = last_scene.get("beats", [])
    if not beats:
        report.add_warning("Last scene has no beats")
        return

    # Check for mismatch indicators
    last_content = beats[-1].get("content", "")
    if novel_ending and last_content:
        # Simple check: if novel_ending contains specific keywords, they should appear
        ending_keywords = set(novel_ending.split()[:10]) if novel_ending else set()
        if ending_keywords:
            match_count = sum(1 for kw in ending_keywords if kw.lower() in last_content.lower())
            if match_count == 0 and len(ending_keywords) >= 3:
                report.add_warning("Last beat content may not match novel ending tone")


def validate_scene_count(data: dict, report: ValidationReport):
    """Warn if episodes have too few or too many scenes."""
    for ep in data.get("episodes", []):
        sc_count = len(ep.get("scenes", []))
        if sc_count < 2:
            report.add_warning(f"Episode '{ep.get('id', ep.get('title', ''))}' has only {sc_count} scene(s)")
        elif sc_count > 12:
            report.add_warning(f"Episode '{ep.get('id', '')}' has {sc_count} scenes (>12 may hurt pacing)")


def validate_duration_estimates(data: dict, report: ValidationReport):
    """Validate duration format and range."""
    dur_pattern = re.compile(r"^\d+(s|m|ms)$")
    for _ep_idx, ep in enumerate(data.get("episodes", [])):
        for _sc_idx, sc in enumerate(ep.get("scenes", [])):
            dur = sc.get("duration_estimate", "")
            if not dur:
                report.add_warning(f"Scene {sc.get('scene_id', '')} missing duration_estimate")
            elif not dur_pattern.match(dur):
                report.add_warning(f"Invalid duration format '{dur}' in scene {sc.get('scene_id', '')}")


def validate_no_extra_characters(data: dict, reference_chars: list[dict], report: ValidationReport):
    """Check no new characters were invented."""
    if not reference_chars:
        return
    ref_names = {c.get("name", "").lower() for c in reference_chars}
    ref_ids = {c.get("id", "") for c in reference_chars}
    for c in data.get("characters", []):
        if c.get("id", "") not in ref_ids and c.get("name", "").lower() not in ref_names:
            report.add_warning(f"Character '{c.get('name', '')}' ({c.get('id', '')}) may be invented")


def validate_characters_enough(data: dict, report: ValidationReport):
    """Check at least 1 character is defined."""
    chars = data.get("characters", [])
    if not chars:
        report.add_error("No characters defined")
    elif len(chars) < 2:
        report.add_warning("Only 1 character defined, story may lack supporting cast")



def validate_character_fidelity(data: dict, novel_text: str, report: ValidationReport):
    """检查剧本中的角色名是否在原文中出现过，标记疑似编造的角色。."""
    if not novel_text or not novel_text.strip():
        return
    novel_lower = novel_text.lower()
    for c in data.get("characters", []):
        name = c.get("name", "")
        if not name or len(name) < 2:
            continue
        # 跳过占位角色名
        if name.lower() in ("protagonist", "antagonist", "character", "protagonist protagonist"):
            report.add_warning(f'Character "{name}" ({c.get("id", "")}) looks like a placeholder name, may be fabricated')
            continue
        name_in_novel = name.lower() in novel_lower
        if not name_in_novel:
            # 对中文名：尝试拆成单个字符确认（中文名2-3字，有可能只出现姓或全名）
            if len(name) <= 3 and any("一" <= ch <= "鿿" for ch in name):
                # 中文名：检查全名是否出现
                if name.lower() not in novel_lower:
                    report.add_warning(f'Character "{name}" ({c.get("id", "")}) not found in original novel text')
            elif name.lower() not in novel_lower:
                report.add_warning(f'Character "{name}" ({c.get("id", "")}) not found in original novel text')



def validate_character_fidelity(data: dict, novel_text: str, report) -> None:
    """Check if screenplay character names appear in the original novel text."""
    if not novel_text or not novel_text.strip():
        return
    nl = novel_text.lower()
    for c in data.get("characters", []):
        name = c.get("name", "")
        if not name or len(name) < 2:
            continue
        nl_name = name.lower()
        if nl_name in ("protagonist", "antagonist", "character", "hero", "villain"):
            report.add_warning("Character " + repr(name) + " looks like a placeholder name")
            continue
        if nl_name not in nl:
            cid = c.get("id", "")
            report.add_warning("Character " + repr(name) + " (" + cid + ") not found in original novel text")


def validate_screenplay_output(
    yaml_str: str,
    novel_text: str = "",
    novel_ending: str = "",
    reference_characters: list[dict] | None = None,
    language: str = "en",
) -> ValidationReport:
    """Run all validations on the output screenplay YAML."""
    report = ValidationReport()

    data = parse_screenplay_yaml(yaml_str)
    if data is None:
        report.add_error("Invalid YAML syntax or empty output")
        return report

    # 1. Required fields
    for field in ("title", "characters", "episodes"):
        if field not in data or not data[field]:
            report.add_error(f"Missing required field: {field}")

    if not report.passed:
        return report

    # 2. Emotion labels
    from .novel_reader import get_emotion_set
    allowed = get_emotion_set(language)
    validate_emotion_labels(data, allowed, report)

    # 3. Character ID consistency
    validate_character_ids(data, report)

    # 4. Characters present field
    validate_characters_present(data, report)

    # 5. Character count
    validate_characters_enough(data, report)

    # 6. No invented characters
    if reference_characters:
        validate_no_extra_characters(data, reference_characters, report)

    # 7. Scene count per episode
    validate_scene_count(data, report)

    # 8. Duration estimates
    validate_duration_estimates(data, report)

    # 9. Ending match
    if novel_ending:
        validate_ending(data, novel_ending, report)

    # 10. Character name fidelity check against original novel text
    if novel_text:
        validate_character_fidelity(data, novel_text, report)

    # 11. Scene ID format check
    char_id_pattern = re.compile(r"^char_\d+$")
    for c in data.get("characters", []):
        cid = c.get("id", "")
        if cid and not char_id_pattern.match(cid):
            report.add_warning(f"Character ID '{cid}' does not follow char_NNN format")

    return report


def check_beat_count(yaml_str: str, min_beats: int = 1) -> bool:
    """Quick check: every scene has at least min_beats beats."""
    data = parse_screenplay_yaml(yaml_str)
    if not data:
        return False
    for ep in data.get("episodes", []):
        for sc in ep.get("scenes", []):
            if len(sc.get("beats", [])) < min_beats:
                return False
    return True
