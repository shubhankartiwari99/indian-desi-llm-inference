from __future__ import annotations

from pathlib import Path

from scripts.decision_trace import build_decision_trace


def _trace_kwargs() -> dict:
    return {
        "user_input": "Need help",
        "intent": "emotional",
        "emotional_lang": "en",
        "emotional_turn_index": 1,
        "previous_skeleton": "A",
        "resolved_skeleton": "B",
        "skeleton_after_guardrail": "B",
        "escalation_state": "none",
        "latched_theme": None,
        "signals": {"overwhelm": False, "resignation": False, "guilt": False, "wants_action": False},
        "eligible_count": 4,
        "selected_variant_indices": {"opener": 0, "validation": 0, "closure": 0},
        "window_size": 8,
        "window_fill": 1,
        "immediate_repeat_blocked": False,
        "fallback": None,
        "cultural": {},
        "invariants": {"selector_called_once": True, "rotation_bounded": True, "deterministic_selector": True},
    }


def test_engine_replay_baseline_lock():
    baseline_path = Path("artifacts/ENGINE_BASELINE_REPLAY.txt")
    expected_hash = baseline_path.read_text(encoding="utf-8").strip()

    trace = build_decision_trace(**_trace_kwargs(), include_tone_profile=True)
    actual_hash = trace["replay_hash"]

    assert actual_hash == expected_hash, (
        "Replay baseline drift detected. "
        "Engine behavior has changed."
    )
