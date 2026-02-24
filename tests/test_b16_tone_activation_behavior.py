from copy import deepcopy

from app.inference import _filter_variants_by_tone
from app.voice.rotation_memory import RotationMemory
from app.voice.select import select_voice_variants
from app.voice.state import SessionVoiceState
from scripts.decision_trace import build_decision_trace


SYNTHETIC_VARIANTS = [
    {"text": "Neutral line", "tone_tags": ["neutral_formal"]},
    {"text": "Warm line", "tone_tags": ["warm_engaged"]},
    {"text": "Universal line"},
]


def _filtered_texts(tone_profile: str) -> list[str]:
    filtered = _filter_variants_by_tone(SYNTHETIC_VARIANTS, tone_profile)
    return [variant["text"] for variant in filtered]


def _resolved_variants(texts: list[str]) -> dict[str, list[str]]:
    return {
        "opener": texts,
        "validation": texts,
        "closure": texts,
    }


def _select_once(*, tone_profile: str, emotional_turn_index: int = 1):
    texts = _filtered_texts(tone_profile)
    state = SessionVoiceState(rotation_memory=RotationMemory(), emotional_turn_index=emotional_turn_index)
    selected = select_voice_variants(
        state,
        "A",
        "en",
        resolved_variants_by_section=_resolved_variants(texts),
    )
    return selected, state


def _trace_kwargs() -> dict:
    return {
        "user_input": "Please explain caching simply.",
        "intent": "emotional",
        "emotional_lang": "en",
        "emotional_turn_index": 1,
        "previous_skeleton": "A",
        "resolved_skeleton": "B",
        "skeleton_after_guardrail": "B",
        "escalation_state": "none",
        "latched_theme": None,
        "signals": {"overwhelm": False, "resignation": False, "guilt": False, "wants_action": False},
        "eligible_count": 3,
        "selected_variant_indices": {"opener": 0, "validation": 0, "closure": 0},
        "window_size": 8,
        "window_fill": 1,
        "immediate_repeat_blocked": False,
        "fallback": None,
        "cultural": {},
        "invariants": {"selector_called_once": True, "rotation_bounded": True, "deterministic_selector": True},
    }


def test_pool_narrowing_warm_keeps_warm_and_universal():
    assert _filtered_texts("warm_engaged") == ["Warm line", "Universal line"]


def test_pool_narrowing_neutral_keeps_neutral_and_universal():
    assert _filtered_texts("neutral_formal") == ["Neutral line", "Universal line"]


def test_pool_narrowing_excludes_mismatched_tag():
    assert "Neutral line" not in _filtered_texts("warm_engaged")


def test_universal_variant_always_eligible_warm():
    assert "Universal line" in _filtered_texts("warm_engaged")


def test_universal_variant_always_eligible_neutral():
    assert "Universal line" in _filtered_texts("neutral_formal")


def test_fallback_to_full_pool_when_all_tags_mismatch():
    synthetic = [{"text": "Neutral only", "tone_tags": ["neutral_formal"]}]
    filtered = _filter_variants_by_tone(synthetic, "warm_engaged")
    assert filtered == synthetic
    assert filtered is synthetic


def test_order_preserved_after_filtering():
    assert _filtered_texts("warm_engaged") == ["Warm line", "Universal line"]


def test_filter_no_mutation_for_synthetic_pool():
    original = deepcopy(SYNTHETIC_VARIANTS)
    _ = _filter_variants_by_tone(SYNTHETIC_VARIANTS, "warm_engaged")
    assert SYNTHETIC_VARIANTS == original


def test_filter_determinism_repeated_calls_identical():
    first = _filtered_texts("warm_engaged")
    second = _filtered_texts("warm_engaged")
    assert first == second


def test_selector_determinism_same_tone_same_selection():
    selected_1, _state_1 = _select_once(tone_profile="warm_engaged")
    selected_2, _state_2 = _select_once(tone_profile="warm_engaged")
    assert selected_1 == selected_2


def test_selector_picks_first_entry_in_filtered_order():
    selected, _state = _select_once(tone_profile="warm_engaged")
    assert selected["opener"] == "Warm line"
    assert selected["validation"] == "Warm line"
    assert selected["closure"] == "Warm line"


def test_selector_changes_when_tone_changes():
    selected_warm, _state_warm = _select_once(tone_profile="warm_engaged")
    selected_neutral, _state_neutral = _select_once(tone_profile="neutral_formal")
    assert selected_warm["opener"] == "Warm line"
    assert selected_neutral["opener"] == "Neutral line"
    assert selected_warm["opener"] != selected_neutral["opener"]


def test_selector_uses_universal_when_only_universal_matches():
    synthetic = [
        {"text": "Firm only", "tone_tags": ["firm_boundary"]},
        {"text": "Universal only"},
    ]
    filtered = _filter_variants_by_tone(synthetic, "warm_engaged")
    state = SessionVoiceState(rotation_memory=RotationMemory(), emotional_turn_index=1)
    selected = select_voice_variants(
        state,
        "A",
        "en",
        resolved_variants_by_section=_resolved_variants([variant["text"] for variant in filtered]),
    )
    assert selected["opener"] == "Universal only"


def test_emotional_turn_index_unchanged_by_filtering_path():
    selected, state = _select_once(tone_profile="warm_engaged", emotional_turn_index=11)
    assert selected["opener"] == "Warm line"
    assert state.emotional_turn_index == 11


def test_selector_invocation_count_increments_normally():
    _selected, state = _select_once(tone_profile="warm_engaged")
    assert state.selector_invocation_count == 1


def test_replay_hash_diverges_when_tone_profile_differs():
    trace_neutral = build_decision_trace(**_trace_kwargs(), tone_profile="neutral_formal")
    trace_warm = build_decision_trace(**_trace_kwargs(), tone_profile="warm_engaged")
    assert trace_neutral["replay_hash"] != trace_warm["replay_hash"]


def test_replay_hash_stable_for_same_tone_profile():
    trace_1 = build_decision_trace(**_trace_kwargs(), tone_profile="warm_engaged")
    trace_2 = build_decision_trace(**_trace_kwargs(), tone_profile="warm_engaged")
    assert trace_1["replay_hash"] == trace_2["replay_hash"]


def test_override_trace_replay_ignores_tone_profile_dimension():
    override_input = "I want to kill myself"
    kwargs = _trace_kwargs()
    kwargs["user_input"] = override_input
    trace_1 = build_decision_trace(**kwargs, tone_profile="neutral_formal")
    trace_2 = build_decision_trace(**kwargs, tone_profile="warm_engaged")
    assert trace_1["guardrail"]["override"] is True
    assert trace_2["guardrail"]["override"] is True
    assert "tone_profile" not in trace_1
    assert "tone_profile" not in trace_2
    assert trace_1["replay_hash"] == trace_2["replay_hash"]
