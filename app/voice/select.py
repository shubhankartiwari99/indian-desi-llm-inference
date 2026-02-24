from typing import Mapping, Optional

from app.voice.contract_loader import get_variants_for
from app.voice.errors import VoiceSelectionError, VoiceStateError
from app.voice.state import SessionVoiceState

WINDOW_SIZES = {
    "A": 6,
    "B": 8,
    "C": 3,
    "D": 4,
}


def _usage_count(window: list, variant_id: int) -> int:
    return sum(1 for item in window if item["variant_id"] == variant_id)


def _last_seen_turn(window: list, variant_id: int):
    for item in reversed(window):
        if item["variant_id"] == variant_id:
            return item["turn_index"]
    return None


def _score_candidate(
    skeleton: str,
    variant_id: int,
    window: list,
    window_size: int,
    current_turn_index: int,
) -> int:
    # Skeleton A: skip penalties on first emotional turn.
    if skeleton == "A" and current_turn_index <= 1:
        return 0

    score = 0
    for item in window:
        if item["variant_id"] != variant_id:
            continue
        distance_from_now = max(0, current_turn_index - item["turn_index"])
        score -= (window_size - distance_from_now)

    usage = _usage_count(window, variant_id)
    window_len = len(window)
    if window_len > 0:
        usage_ratio = usage / window_len
        if skeleton == "C":
            # Skeleton C override: ignore 50% cap unless extreme repetition.
            if usage == window_len:
                score -= window_size * 2
        else:
            if usage_ratio > 0.5:
                score -= window_size * 2

    return score


def _eligible_candidates(skeleton: str, candidate_ids: list, window: list) -> list:
    if not window:
        return list(candidate_ids)

    last_variant_id = window[-1]["variant_id"]
    if last_variant_id not in candidate_ids:
        return list(candidate_ids)

    if len(candidate_ids) <= 1:
        return list(candidate_ids)

    filtered = [candidate_id for candidate_id in candidate_ids if candidate_id != last_variant_id]
    if filtered:
        return filtered

    # Skeleton C: allow repetition if immediate-repeat filtering empties pool.
    if skeleton == "C":
        return list(candidate_ids)
    return filtered


def _tie_break(candidate_ids: list, window: list) -> int:
    # 1) Least recently used
    # 2) Lowest usage count
    # 3) Lowest variant index
    def tie_key(candidate_id: int):
        last_seen = _last_seen_turn(window, candidate_id)
        least_recent_rank = last_seen if last_seen is not None else -1
        usage = _usage_count(window, candidate_id)
        return (least_recent_rank, usage, candidate_id)

    return min(candidate_ids, key=tie_key)


def _validate_state_for_selection(session_state: SessionVoiceState) -> None:
    if session_state is None:
        raise VoiceStateError("Missing session state")
    if not hasattr(session_state, "rotation_memory") or session_state.rotation_memory is None:
        raise VoiceStateError("Missing rotation memory")
    if not isinstance(getattr(session_state, "emotional_turn_index", None), int):
        raise VoiceStateError("Invalid emotional_turn_index type")
    if session_state.emotional_turn_index < 0:
        raise VoiceStateError("Negative emotional_turn_index")
    if not hasattr(session_state.rotation_memory, "read_window"):
        raise VoiceStateError("rotation_memory.read_window unavailable")
    if not hasattr(session_state.rotation_memory, "record_usage"):
        raise VoiceStateError("rotation_memory.record_usage unavailable")


def select_voice_variants(
    session_state: SessionVoiceState,
    skeleton: str,
    language: str,
    resolved_variants_by_section: Optional[Mapping[str, list]] = None,
):
    """
    Phase 3B:
    Deterministic memory-aware selection.
    No randomness, no semantic scoring, no cross-session memory.
    """
    _validate_state_for_selection(session_state)
    sections = ["opener", "validation", "closure"]
    if skeleton == "D":
        sections = ["opener", "action", "closure"]

    session_state.selector_invocation_count += 1
    selected = {}
    current_turn_index = int(session_state.emotional_turn_index or 0)
    window_size = WINDOW_SIZES.get(skeleton, 6)

    for section in sections:
        if resolved_variants_by_section is not None and section in resolved_variants_by_section:
            variants = resolved_variants_by_section[section]
        else:
            variants = get_variants_for(skeleton, language, section)
        if not variants:
            raise VoiceSelectionError(f"No variants found for {skeleton}/{language}/{section}")

        pool_key = (skeleton, language, section)
        try:
            window = session_state.rotation_memory.read_window(
                pool_key,
                window_size=window_size,
                current_turn_index=current_turn_index,
            )
        except (TypeError, AttributeError, KeyError, ValueError) as exc:
            raise VoiceStateError(f"Failed to read rotation window for {pool_key}") from exc
        if not isinstance(window, list):
            raise VoiceStateError(f"Rotation window is not a list for {pool_key}")
        for item in window:
            if not isinstance(item, dict) or "variant_id" not in item or "turn_index" not in item:
                raise VoiceStateError(f"Malformed rotation window entry for {pool_key}: {item!r}")
        candidate_ids = list(range(len(variants)))
        eligible = _eligible_candidates(skeleton, candidate_ids, window)
        if not eligible:
            raise VoiceSelectionError(f"No eligible variants for {skeleton}/{language}/{section}")

        scores = {
            candidate_id: _score_candidate(
                skeleton=skeleton,
                variant_id=candidate_id,
                window=window,
                window_size=window_size,
                current_turn_index=current_turn_index,
            )
            for candidate_id in eligible
        }
        best_score = max(scores.values())
        top_candidates = [candidate_id for candidate_id in eligible if scores[candidate_id] == best_score]
        variant_id = _tie_break(top_candidates, window)

        selected[section] = variants[variant_id]

        # Memory update happens only after final deterministic selection.
        try:
            session_state.rotation_memory.record_usage(pool_key, variant_id, current_turn_index)
        except (TypeError, AttributeError, KeyError, ValueError) as exc:
            raise VoiceStateError(f"Failed to record rotation usage for {pool_key}") from exc

    return selected
