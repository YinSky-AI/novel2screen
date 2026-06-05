# Novel2Screen Fidelity Scrubber - hallucination detection layer.

def _name_in_text(name: str, text: str) -> bool:
    name_l = name.lower().strip()
    text_l = text.lower()
    if name_l in ("protagonist", "antagonist", "character", "narrator", "hero", "villain"):
        return False
    if name_l in text_l:
        return True
    for part in name.split():
        p = part.strip('.,;:!?" ')
        if len(p) >= 2 and p.lower() in text_l:
            return True
    return False


def detect_fabricated_characters(chars: list, novel_text: str) -> list:
    suspicious = []
    for c in chars:
        nm = c.get("name", "") if isinstance(c, dict) else ""
        cid = c.get("id", "") if isinstance(c, dict) else ""
        if not nm or len(nm) < 2:
            continue
        if nm.lower() in ("protagonist", "antagonist", "character", "hero", "villain"):
            suspicious.append({"id": cid, "name": nm, "reason": "placeholder name"})
        elif novel_text and not _name_in_text(nm, novel_text):
            suspicious.append({"id": cid, "name": nm, "reason": "not found in original novel"})
    return suspicious


def detect_fabricated_locations(locations: list, novel_text: str) -> list:
    suspicious = []
    for loc in locations:
        nm = loc.get("name", "") if isinstance(loc, dict) else ""
        if not nm or len(nm) < 2:
            continue
        if nm.lower() in ("main setting", "unknown", "somewhere"):
            suspicious.append({"name": nm, "reason": "placeholder"})
        elif novel_text and not _name_in_text(nm, novel_text):
            suspicious.append({"name": nm, "reason": "not found in original novel"})
    return suspicious


def validate_character_ids_in_episodes(episodes: list, valid_ids: set) -> list:
    violations = []
    if not valid_ids:
        return violations
    for ep in episodes:
        if not isinstance(ep, dict):
            continue
        eid = ep.get("id", "")
        for sc in ep.get("scenes", []):
            if not isinstance(sc, dict):
                continue
            sid = sc.get("scene_id", "")
            for bi, beat in enumerate(sc.get("beats", [])):
                cid = beat.get("character_id") if isinstance(beat, dict) else None
                if beat.get("type") == "dialogue" and cid and cid not in valid_ids:
                    violations.append(f"Episode {eid}, Scene {sid}, Beat {bi+1}: char {cid} not valid")
    return violations


def run_fidelity_check(preprocess_output: dict, batch_plan_output: dict, novel_text: str) -> dict:
    chars = preprocess_output.get("characters", []) if isinstance(preprocess_output, dict) else []
    locs = preprocess_output.get("locations", []) if isinstance(preprocess_output, dict) else []
    episodes = batch_plan_output.get("episodes", []) if isinstance(batch_plan_output, dict) else []

    fabricated_chars = detect_fabricated_characters(chars, novel_text)
    fabricated_locs = detect_fabricated_locations(locs, novel_text)
    valid_ids = {c.get("id", "") for c in chars if isinstance(c, dict) and c.get("id")}
    id_violations = validate_character_ids_in_episodes(episodes, valid_ids)
    total = len(fabricated_chars) + len(fabricated_locs) + len(id_violations)
    score = max(0.0, 1.0 - total * 0.15)

    return {
        "fabricated_chars": fabricated_chars,
        "fabricated_locs": fabricated_locs,
        "id_violations": id_violations,
        "fidelity_score": score,
    }
